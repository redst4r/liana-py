import numpy as np
import pandas as pd
import logging
from tqdm import tqdm

from scipy.sparse import isspmatrix_csr, csr_matrix

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.model_selection import KFold, cross_val_predict
import statsmodels.api as sm

from anndata import AnnData
from mudata import MuData

class MistyData(MuData):
    # TODO: change to SpatialData when Squidpy is also updated
    def __init__(self, data, obs=None, spatial_key='spatial', **kwargs):
        """
        Construct a MistyData object from a dictionary of views (anndatas).
        
        Parameters
        ----------
        data : `dict`
            Dictionary of views (anndatas) or an mdata object.
            Requires an intra-view called "intra".
        obs : `pd.DataFrame`
            DataFrame of observations. If None, the obs of the intra-view is used.
        spatial_key : `str`
            Key in the .obsm attribute of each view that contains the spatial coordinates.
            Default is 'spatial'.
        **kwargs : `dict`
            Keyword arguments passed to the MuData Super class
        """
        
        if isinstance(data, MuData):
            temp = {}
            for view in list(data.mod.keys()):
                temp[view] = data.mod[view]
            data = temp
        
        super().__init__(data, **kwargs)
        self.view_names = list(self.mod.keys())
        self.spatial_key = spatial_key
        self._check_views()
        self.obs = obs if obs is not None else self.mod['intra'].obs

    def _check_views(self):
        assert isinstance(self, MuData), "views must be a MuData object"
        assert "intra" in self.view_names, "views must contain an intra view"
        
        for view in self.view_names:
            if not isspmatrix_csr(self.mod[view].X):
                 logging.warning(f"view {view} is not a csr_matrix. Converting to csr_matrix")
                 self.mod[view].X = csr_matrix(self.mod[view].X)
            if view=="intra":
                continue
            if f"{self.spatial_key}_connectivities" not in self.mod[view].obsp.keys():
                raise ValueError(f"view {view} does not contain `{self.spatial_key}_connectivities` key in .obsp")

    
    def _get_conn(self, view_name):
        return self.mod[view_name].obsp[f"{self.spatial_key}_connectivities"]
    
    # NOTE: having this as a call fun would mean that it would only work when a misty object is created
    # but not when a mudata object in misty format is loaded from disk
    def __call__(self,
                 model='rf',
                 bypass_intra = False,
                 predict_self = False,
                 k_cv = 10,
                 alphas = [0.1, 1, 10],
                 intra_groupby = None,
                 extra_groupby = None,
                 n_jobs = -1,
                 seed = 1337,
                 inplace=True,
                 verbose=False,
                 **kwargs
                 ):
        """
        A Multi-view Learning for dissecting Spatial Transcriptomics data (MISTY) model.
        
        Parameters
        ----------
        n_estimators : `int`, optional (default: 100)
            Number of trees in the random forest models used to model single views
        model : `str`, optional (default: 'rf')
            Model used to model the single views. Default is 'rf'.
            Can be either 'rf' (random forest) or 'linear' (linear regression).
        bypass_intra : `bool`, optional (default: False)
            Whether to bypass modeling the intraview features importances via LOFO
        intra_groupby : `str`, optional (default: None)
            Column in the .obs attribute used to group cells in the intra-view
            If None, all cells are considered as one group
        extra_groupby : `str`, optional (default: None)
            Column in the .obs attribute used to group cells in the extra-view(s)
            If None, all cells are considered as one group.
        alphas : `list`, optional (default: [0.1, 1, 10])
            List of alpha values used to choose from, that control the strength of the ridge regression,
            used for the multi-view part of the model
        k_cv : `int`, optional (default: 10)
            Number of folds for cross-validation used in the multi-view model, and single-view models if
            model is 'linear'.
        n_jobs : `int`, optional (default: -1)
            Number of cores used to construct random forest models
        seed : `int`, optional (default: 1337)
            Specify random seed for reproducibility
        inplace : `bool`, optional (default: True)
            Whether to write the results to the .uns attribute of the object or return 
            two DataFrames, one for target metrics and one for importances.
        **kwargs : `dict`
            Keyword arguments passed to the Regressors. Note that n_jobs & random_state are already set.
        
        Returns
        -------
        If inplace is True, the results are written to the `.uns` attribute of the object.
        Otherwise two DataFrames are returned, one for target metrics and one for importances.

        """
        
        # TODO: function that checks if the groupby is in the obs
        # and does this for both extra & intra
        intra_groups = np.unique(self.obs[intra_groupby]) if intra_groupby else [None]
        extra_groups = np.unique(self.obs[extra_groupby]) if extra_groupby else [None]
        
        view_str = list(self.view_names)
        
        if bypass_intra:
            view_str.remove('intra')
        intra = self.mod['intra']
        
        # init list to store the results for each intra group and env group as dataframe;
        targets_list, importances_list = [], []
        intra_features = intra.var_names.to_list()
                
        progress_bar = tqdm(intra_features, disable=not verbose)
        # loop over each target and build one RF model for each view
        for target in (progress_bar):
            if verbose:
                progress_bar.set_description(f"Now learning: {target}")
            
            for intra_group in intra_groups:
                intra_obs_msk = intra.obs[intra_groupby] == \
                        intra_group if intra_group else np.ones(intra.shape[0], dtype=bool)
                
                # to array
                y = intra[intra_obs_msk, target].X.toarray().reshape(-1)
                # intra is always non-self, while other views can be self
                predictors_nonself, insert_index = _get_nonself(target, intra_features)

                # TODO: rename to target_importances
                importance_dict = {}
                
                # model the intraview
                if not bypass_intra:
                    predictions_intra, importance_dict["intra"] = _single_view_model(y,
                                                                                     intra,
                                                                                     intra_obs_msk,
                                                                                     predictors_nonself,
                                                                                     model=model,
                                                                                     k_cv=k_cv,
                                                                                     seed=seed,
                                                                                     n_jobs=n_jobs,
                                                                                     **kwargs
                                                                                     )
                    if insert_index is not None and predict_self: 
                        # add self-interactions as nan
                        importance_dict["intra"][target] = np.nan

                # loop over the group_views_by
                for extra_group in extra_groups:
                    # store the oob predictions for each view to construct predictor matrix for meta model
                    predictions_list = []

                    if not bypass_intra:
                        predictions_list.append(predictions_intra)

                    # model the juxta and paraview (if applicable)
                    for view_name in [v for v in view_str if v != "intra"]:
                        extra = self.mod[view_name]
                        
                        extra_features = extra.var_names.to_list()
                        _predictors, _ =  _get_nonself(target, extra_features) if not predict_self else (extra_features, None)
                        
                        extra_obs_msk = self.obs[extra_groupby] == extra_group if extra_group is not None else None
                        
                        # NOTE: indexing here is expensive, but we do it to avoid memory issues
                        connectivity = self._get_conn(view_name)
                        view = _mask_connectivity(extra, connectivity, extra_obs_msk, _predictors)
                        
                        predictions_extra, importance_dict[view_name] = \
                            _single_view_model(y,
                                               view,
                                               intra_obs_msk,
                                               _predictors, 
                                               model=model,
                                               k_cv=k_cv,
                                               seed=seed,
                                               n_jobs=n_jobs,
                                               **kwargs
                                               )
                        predictions_list.append(predictions_extra)

                    # train the meta model with k-fold CV
                    intra_r2, multi_r2, coefs = _multi_model(y,
                                                             np.column_stack(predictions_list),
                                                             intra_group,
                                                             bypass_intra,
                                                             view_str,
                                                             k_cv,
                                                             alphas, 
                                                             seed
                                                             )
                    
                    # write the results to a dataframe
                    targets_df = _format_targets(target,
                                                 intra_group,
                                                 extra_group,
                                                 view_str,
                                                 intra_r2,
                                                 multi_r2,
                                                 coefs
                                                 )
                    targets_list.append(targets_df)
                    
                    importances_df = _format_importances(target=target, 
                                                         intra_group=intra_group, 
                                                         extra_group=extra_group,
                                                         importance_dict=importance_dict
                                                         )
                    importances_list.append(importances_df)


        # create result dataframes
        target_metrics, importances = _concat_dataframes(targets_list,
                                                         importances_list,
                                                         view_str)
        
        if inplace:
            self.uns['target_metrics'] = target_metrics
            self.uns['interactions'] = importances
        else:
            return target_metrics, importances


def _create_dict(**kwargs):
    return {k: v for k, v in kwargs.items() if v is not None}

def _format_targets(target, intra_group, extra_group, view_str, intra_r2, multi_r2, coefs):
    # TODO: Remove dot from column names
    d = _create_dict(target=target,
                     intra_group=intra_group,
                     extra_group=extra_group,
                     intra_R2=intra_r2,
                     multi_R2=multi_r2,
                     gain_R2=multi_r2 - intra_r2,
                     )
    
    target_df = pd.DataFrame(d, index=[0])
    target_df[view_str] = coefs
    
    return target_df


def _format_importances(target, intra_group, extra_group, importance_dict):
    
    importances_df = pd.DataFrame(importance_dict).reset_index().rename(columns={'index': 'predictor'})
    importances_df[['target', 'intra_group', 'extra_group']] = target, intra_group, extra_group
        
    return importances_df


def _concat_dataframes(targets_list, importances_list, view_str):
    target_metrics = pd.concat(targets_list, axis=0, ignore_index=True)
    
    target_metrics.loc[:, view_str] = target_metrics.loc[:, view_str].clip(lower=0)
    target_metrics.loc[:, view_str] = target_metrics.loc[:, view_str].div(target_metrics.loc[:, view_str].sum(axis=1), axis=0)
    
    importances = pd.concat(importances_list, axis=0, ignore_index=True)
    importances = pd.melt(importances,
                          id_vars=["target", "predictor", "intra_group", "extra_group"], 
                          value_vars=view_str, var_name="view", value_name="importances")
    
    # drop intra and extra group columns if they are all None
    importances = importances.dropna(axis=1, how='all')
    
    return target_metrics, importances


def _single_view_model(y, view, intra_obs_msk, predictors, model, k_cv, seed, n_jobs, **kwargs):
    X = view[intra_obs_msk, predictors].X.toarray()
    
    if model=='rf':
        model = RandomForestRegressor(oob_score=True,
                                      n_jobs=n_jobs,
                                      random_state=seed,
                                      **kwargs,
                                      )
        # Model is a RandomForestRegressor
        model = model.fit(y=y, X=X)
        predictions = model.oob_prediction_
        importances = model.feature_importances_
        
    elif model=='linear':
        model = LinearRegression(n_jobs=1, **kwargs)
        predictions = cross_val_predict(model, X, y,
                                        cv=KFold(n_splits=k_cv,
                                                 random_state = seed,
                                                 shuffle=True),
                                        n_jobs=n_jobs
                                        )
        # NOTE: I use ols t-values for feature importances
        importances = sm.OLS(y, X).fit().tvalues
        # importances = model.fit(X=X, y=y).coef_
        # importances = sm.OLS(y, X).fit().params
        
    else:
        raise ValueError(f"model {model} is not supported")
    
    named_importances = dict(zip(predictors, importances))
    
    return predictions, named_importances


def _multi_model(y, predictions, intra_group, bypass_intra, view_str, k_cv, alphas, seed):
    if predictions.shape[0] < k_cv:
        logging.warn(f"Number of samples in {intra_group} is less than k_cv. "
                     "{intra_group} values set to NaN")
        return np.nan, np.nan, np.repeat(np.nan, len(view_str))
        
    kf = KFold(n_splits=k_cv, shuffle=True, random_state=seed)
    R2_vec_intra, R2_vec_multi = np.zeros(k_cv), np.zeros(k_cv)
    coef_mtx = np.zeros((k_cv, len(view_str)))
    
    for cv_idx, (train_index, test_index) in enumerate(kf.split(predictions)):
        ridge_multi_model = RidgeCV(alphas=alphas).fit(X=predictions[train_index], y=y[train_index])
        R2_vec_multi[cv_idx] = ridge_multi_model.score(X=predictions[test_index], y=y[test_index])
        coef_mtx[cv_idx, :] = ridge_multi_model.coef_

        if not bypass_intra: 
            # NOTE: first column of obp is always intra only prediction if bypass_intra is False
            obp_train = predictions[train_index, 0].reshape(-1, 1)
            obp_test = predictions[test_index, 0].reshape(-1, 1)
            
            ridge_intra_model = RidgeCV(alphas=alphas).fit(X=obp_train, y=y[train_index])
            R2_vec_intra[cv_idx] = ridge_intra_model.score(X=obp_test, y=y[test_index])
            
        # TODO: misty's ridgeCV p-values (ridge::pvals) are calculated as in 
        # https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-12-372#Sec2
        # these are needed for the scaling of RF importances

    intra_r2 = R2_vec_intra.mean() if not bypass_intra else 0
    
    return intra_r2, R2_vec_multi.mean(), coef_mtx.mean(axis=0)


def _mask_connectivity(adata, connectivity, extra_obs_msk, predictors):
    
    weights = connectivity.copy()
    if extra_obs_msk is not None:
        weights[:, ~extra_obs_msk] = 0
    X = weights @ adata[:, predictors].X
    view = AnnData(X=X, obs=adata.obs, var=pd.DataFrame(index=predictors), dtype='float32')
    
    return view

def _get_nonself(target, predictors):
    if target in predictors:
        insert_idx = np.where(np.array(predictors) == target)[0][0]
        predictors_subset = predictors.copy()
        predictors_subset.pop(insert_idx)
    else:
        predictors_subset = predictors
        insert_idx = None
    return predictors_subset, insert_idx
