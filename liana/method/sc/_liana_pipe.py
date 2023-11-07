from __future__ import annotations

from functools import reduce

import anndata
import pandas
import scanpy as sc
import pandas as pd
import numpy as np

from liana.method._pipe_utils import prep_check_adata, assert_covered, \
    filter_resource, filter_reassemble_complexes
from liana.method._pipe_utils._common import _join_stats
from liana.resource._select_resource import _handle_resource
from liana.method._pipe_utils._reassemble_complexes import explode_complexes
from liana.method._pipe_utils._get_mean_perms import _get_means_perms, _get_mat_idx
from liana.method._pipe_utils._aggregate import _aggregate
from liana.method._pipe_utils._common import _get_props
from liana._constants import MethodColumns as M, CommonColumns as C, \
                            PrimaryColumns as P, InternalValues as I

def liana_pipe(adata: anndata.AnnData,
               groupby: str,
               resource_name: str,
               resource: pd.DataFrame | None,
               interactions,
               expr_prop: float,
               min_cells: int,
               base: float,
               de_method: str,
               n_perms: int,
               seed: int,
               verbose: bool,
               use_raw: bool,
               layer: str | None,
               supp_columns: list | None = None,
               return_all_lrs: bool = False,
               _score=None,
               _methods: list = None,
               _consensus_opts: list = None,
               _aggregate_method: str | None = None
               ):
    """
    Parameters
    ----------
    adata
        Annotated data object.
    groupby
        The key of the observations grouping to consider.
    resource_name
        Name of the resource to be loaded and use for ligand-receptor inference.
    resource
        Parameter to enable external resources to be passed. Expects a pandas dataframe
        with [`ligand`, `receptor`] columns. None by default. If provided will overrule
        the resource requested via `resource_name`
    expr_prop
        Minimum expression proportion for the ligands/receptors (and their subunits) in the
         corresponding cell identities. Set to `0`, to return unfiltered results.
    min_cells
        Minimum cells per cell identity
    base
        The base by which to do expm1 (relevant only for 1vsRest logFC calculation)
    de_method
        Differential expression method. `scanpy.tl.rank_genes_groups` is used to rank genes
        according to 1vsRest. The default method is 't-test'. Only relevant if p-values
        are included in `supp_cols`
    n_perms
        n permutations (relevant only for permutation-based methods)
    seed
        Random seed for reproducibility
    verbose
        Verbosity flag
    use_raw
        Use raw attribute of adata if present.
    layer
        Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.
    supp_columns
        additional columns to be added to the output of each method.
    return_all_lrs
        Bool whether to return all LRs, or only those that surpass the expr_prop threshold.
        `False` by default.
    _score
        Instance of Method classes (None by default - returns LR stats - no methods used).
    _methods
        Methods to be run (only relevant for consensus).
    _consensus_opts
        Ways to aggregate interactions across methods by default does all aggregations (['Specificity', 'Magnitude']).
    _aggregate_method
        RobustRankAggregate('rra') or mean rank ('mean').

    Returns
    -------
    A adata frame with ligand-receptor results

    """
    _key_cols = P.primary

    if _score is not None:
        _complex_cols, _add_cols = _score.complex_cols, _score.add_cols
    else:
        _complex_cols = [C.ligand_means, C.receptor_means]
        _add_cols = M.get_all_values()

    if n_perms is None:
        _consensus_opts = 'Magnitude'

    if supp_columns is None:
        supp_columns = []
    _add_cols = _add_cols + [P.ligand, P.receptor,
                             C.ligand_props, C.receptor_props] + supp_columns

    # initialize mat_mean for sca
    mat_mean = None
    mat_max = None

    # Check and Reformat Mat if needed
    assert groupby is not None
    adata = prep_check_adata(adata=adata,
                             groupby=groupby,
                             min_cells=min_cells,
                             use_raw=use_raw,
                             layer=layer,
                             verbose=verbose)

    # get mat mean for SCA (before reducing the features)
    if M.mat_mean in _add_cols:
        mat_mean = np.mean(adata.X, dtype='float32')

    # get mat max for CellChat
    if M.mat_max in _add_cols:
        mat_max = adata.X.max()
        assert isinstance(mat_max, np.float32)

    resource = _handle_resource(interactions=interactions,
                                resource=resource,
                                resource_name=resource_name,
                                verbose=verbose)

    # explode complexes/decomplexify
    resource = explode_complexes(resource)

    # Check overlap between resource and adata
    assert_covered(np.union1d(np.unique(resource[P.ligand]),
                              np.unique(resource[P.receptor])),
                   adata.var_names, verbose=verbose)

    # Filter Resource
    resource = filter_resource(resource, adata.var_names)

    if verbose:
        print(f"Generating ligand-receptor stats for {adata.shape[0]} samples "
              f"and {adata.shape[1]} features")

    # Create Entities
    entities = np.union1d(np.unique(resource[P.ligand]),
                          np.unique(resource[P.receptor]))

    # Filter to only include the relevant genes
    adata = adata[:, np.intersect1d(entities, adata.var.index)]

    # Get lr results
    lr_res = _get_lr(adata=adata,
                     resource=resource,
                     mat_mean=mat_mean,
                     mat_max=mat_max,
                     relevant_cols=_key_cols + _add_cols + _complex_cols,
                     de_method=de_method,
                     base=base,
                     verbose=verbose
                     )

    # Mean Sums required for NATMI (note done on subunits also)
    if M.ligand_means_sums in _add_cols:
        on = [x for x in P.complete if x != P.source]
        lr_res = _sum_means(lr_res, what=C.ligand_means, on=on)
    if M.receptor_means_sums in _add_cols:
        on = [x for x in P.complete if x != P.target]
        lr_res = _sum_means(lr_res, what=C.receptor_means, on=on)

    # Calculate Score
    if _score is not None:
        if _score.method_name == "Rank_Aggregate":
            # Run all methods in consensus
            lrs = {}
            for method in _methods:
                if verbose:
                    print(f"Running {method.method_name}")

                lrs[method.method_name] = \
                    _run_method(lr_res=lr_res.copy(),
                                adata=adata,
                                expr_prop=expr_prop,
                                _score=method,
                                _key_cols=_key_cols,
                                _complex_cols=method.complex_cols,
                                _add_cols=method.add_cols,
                                n_perms=n_perms,
                                seed=seed,
                                return_all_lrs=return_all_lrs,
                                verbose=verbose,
                                _aggregate_flag=True
                                )
            if _consensus_opts is not False:
                lr_res = _aggregate(lrs,
                                    consensus=_score,
                                    aggregate_method=_aggregate_method,
                                    _key_cols=_key_cols,
                                    _consensus_opts=_consensus_opts,
                                    )
            else:  # Return by method results as they are
                return lrs
        else:  # Run the specific method in mind
            lr_res = _run_method(lr_res=lr_res,
                                 adata=adata,
                                 expr_prop=expr_prop,
                                 _score=_score, _key_cols=_key_cols,
                                 _complex_cols=_complex_cols,
                                 _add_cols=_add_cols,
                                 n_perms=n_perms,
                                 return_all_lrs=return_all_lrs,
                                 verbose=verbose,
                                 seed=seed)
    else:  # Just return lr_res
        lr_res = filter_reassemble_complexes(lr_res=lr_res,
                                             _key_cols=_key_cols,
                                             expr_prop=expr_prop,
                                             complex_cols=_complex_cols,
                                             return_all_lrs=return_all_lrs)

    if _score is not None:
        orderby, ascending =  (_score.magnitude, _score.magnitude_ascending) if _score.magnitude is not None \
            else (_score.specificity, _score.specificity_ascending)

        lr_res = lr_res.sort_values(by=orderby, ascending=ascending)

    return lr_res


def _get_lr(adata, resource, relevant_cols, mat_mean, mat_max, de_method, base, verbose):
    labels = adata.obs[I.label].cat.categories

    # Method-specific stats
    connectome_flag = (M.ligand_zscores in relevant_cols) | (
                M.receptor_zscores in relevant_cols)
    if connectome_flag:
        adata.layers['scaled'] = sc.pp.scale(adata, copy=True).X

    logfc_flag = (M.ligand_logfc in relevant_cols) | (
            M.receptor_logfc in relevant_cols)
    if logfc_flag:
        if 'log1p' in adata.uns_keys():
            if (adata.uns['log1p']['base'] is not None) & verbose:
                print("Assuming that counts were `natural` log-normalized!")
        elif ('log1p' not in adata.uns_keys()) & verbose:
            print("Assuming that counts were `natural` log-normalized!")
        adata.layers['normcounts'] = adata.X.copy()
        adata.layers['normcounts'].data = _expm1_base(adata.X.data, base)

    # initialize dict
    dedict = {}

    # Calc pvals + other stats per gene or not
    rank_genes_bool = (C.ligand_pvals in relevant_cols) | (C.receptor_pvals in relevant_cols)
    if rank_genes_bool:
        adata = sc.tl.rank_genes_groups(adata, groupby=I.label,
                                        method=de_method, use_raw=False,
                                        copy=True)

    for label in labels:
        temp = adata[adata.obs[I.label] == label, :]
        a = _get_props(temp.X)
        stats = pd.DataFrame({'names': temp.var_names, 'props': a}). \
            assign(label=label).sort_values('names')
        if rank_genes_bool:
            pvals = sc.get.rank_genes_groups_df(adata, label)
            stats = stats.merge(pvals)
        dedict[label] = stats

    # check if genes are ordered correctly
    if not list(adata.var_names) == list(dedict[labels[0]]['names']):
        raise AssertionError("Variable names did not match DE results!")

    # Calculate Mean, logFC and z-scores by group
    for label in labels:
        temp = adata[adata.obs[I.label].isin([label])]
        dedict[label]['means'] = temp.X.mean(axis=0).A.flatten()
        if connectome_flag:
            dedict[label]['zscores'] = temp.layers['scaled'].mean(axis=0)
        if logfc_flag:
            dedict[label]['logfc'] = _calc_log2fc(adata, label)
        if isinstance(mat_max, np.float32):  # cellchat flag
            dedict[label]['trimean'] = _trimean(temp.X / mat_max)

    # Create df /w cell identity pairs
    # pd.DataFrame(list(product(labels, labels))); TODO: check this
    pairs = (pd.DataFrame(np.array(np.meshgrid(labels, labels))
                          .reshape(2, np.size(labels) * np.size(labels)).T)
             .rename(columns={0: P.source, 1: P.target}))

    # Join Stats
    lr_res = pd.concat(
        [_join_stats(source, target, dedict, resource) for source, target in
         zip(pairs[P.source], pairs[P.target])]
    )

    if M.mat_mean in relevant_cols:
        assert isinstance(mat_mean, np.float32)
        lr_res[M.mat_mean] = mat_mean

    # NOTE: this is not needed
    if isinstance(mat_max, np.float32):
        lr_res[M.mat_max] = mat_max

    # subset to only relevant columns
    relevant_cols = np.intersect1d(relevant_cols, lr_res.columns)

    return lr_res[relevant_cols]


def _sum_means(lr_res, what, on):
    return lr_res.join(lr_res.groupby(on)[what].sum(), on=on, rsuffix='_sums')


def _calc_log2fc(adata, label) -> np.ndarray:
    # Get subject vs rest cells
    subject = adata[adata.obs[I.label].isin([label])]
    rest = adata[~adata.obs[I.label].isin([label])]

    # subject and rest means
    subj_means = subject.layers['normcounts'].mean(0).A.flatten()
    rest_means = rest.layers['normcounts'].mean(0).A.flatten()

    # log2 + 1 transform
    subj_log2means = np.log2(subj_means + 1)
    loso_log2means = np.log2(rest_means + 1)

    logfc_vec = subj_log2means - loso_log2means

    return logfc_vec


def _expm1_base(X, base):
    return np.power(base, X) - 1


def _run_method(lr_res: pandas.DataFrame,
                adata: anndata.AnnData,
                expr_prop: float,
                _score,
                _key_cols: list,
                _complex_cols: list,
                _add_cols: list,
                n_perms: int,
                seed: int,
                return_all_lrs: bool,
                verbose: bool,
                _aggregate_flag: bool = False  # Indicates whether we're generating the consensus
                ) -> pd.DataFrame:
    # re-assemble complexes - specific for each method
    lr_res = filter_reassemble_complexes(lr_res=lr_res,
                                         _key_cols=_key_cols,
                                         expr_prop=expr_prop,
                                         return_all_lrs=return_all_lrs,
                                         complex_cols=_complex_cols)

    _add_cols = _add_cols + [P.ligand, P.receptor]
    relevant_cols = reduce(np.union1d, [_key_cols, _complex_cols, _add_cols])
    if return_all_lrs:
        relevant_cols = list(relevant_cols) + [I.lrs_to_keep]
        # separate those that pass from rest
        rest_res = lr_res[~lr_res[I.lrs_to_keep]]
        rest_res = rest_res[relevant_cols]
        lr_res = lr_res[lr_res[I.lrs_to_keep]]
    lr_res = lr_res[relevant_cols]

    if (M.mat_max in _add_cols) & (_score.method_name == "CellChat"):
        # CellChat matrix_max
        norm_factor = np.unique(lr_res[M.mat_max].values)[0]
        agg_fun = _trimean
    else:
        norm_factor = None
        agg_fun = np.mean

    if _score.permute:
        # get permutations
        if n_perms is not None:
            perms = _get_means_perms(adata=adata,
                                     n_perms=n_perms,
                                     seed=seed,
                                     agg_fun=agg_fun,
                                     norm_factor=norm_factor,
                                     verbose=verbose)
            # get tensor indexes for ligand, receptor, source, target
            ligand_idx, receptor_idx, source_idx, target_idx = _get_mat_idx(adata, lr_res)

            # ligand and receptor perms
            ligand_stat_perms = perms[:, source_idx, ligand_idx]
            receptor_stat_perms = perms[:, target_idx, receptor_idx]
            # stack them together
            perm_stats = np.stack((ligand_stat_perms, receptor_stat_perms), axis=0)
        else:
            perm_stats = None
            _score.specificity = None

        scores = _score.fun(x=lr_res,
                            perm_stats=perm_stats)
    else:  # non-perm funs
        scores = _score.fun(x=lr_res)

    lr_res.loc[:, _score.magnitude] = scores[0]
    lr_res.loc[:, _score.specificity] = scores[1]


    if return_all_lrs:
        # re-append rest of results
        lr_res = pd.concat([lr_res, rest_res], copy=False)
        if _score.magnitude is not None:
            fill_value = _assign_min_or_max(lr_res[_score.magnitude],
                                            _score.magnitude_ascending)
            lr_res.loc[~lr_res[I.lrs_to_keep], _score.magnitude] = fill_value
        if _score.specificity is not None:
            fill_value = _assign_min_or_max(lr_res[_score.specificity],
                                            _score.specificity_ascending)
            lr_res.loc[~lr_res[I.lrs_to_keep], _score.specificity] = fill_value

    if _aggregate_flag:  # if consensus keep only the keys and the method scores
        lr_res = lr_res[_key_cols + [_score.magnitude, _score.specificity]]

    # remove redundant cols for some scores
    if (_score.magnitude is None) | (_score.specificity is None):
        lr_res = lr_res.drop([None], axis=1)

    return lr_res


def _assign_min_or_max(x, x_ascending):
    if x_ascending:
        return np.max(x)
    else:
        return np.min(x)


def _trimean(a, axis=0):
    return np.mean(
        np.quantile(a.A,
                    q=[0.25, 0.5, 0.5, 0.75],
                    axis=axis),
        axis=axis)
