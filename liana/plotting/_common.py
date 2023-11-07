import numpy as np
import pandas as pd

from liana._constants import Keys as K

def _check_var(liana_res, var_name, var):
    if var is None:
        raise ValueError(f'`{var_name}` must be provided!')
    if var not in liana_res.columns:
        raise ValueError(f'`{var}` ({var_name}) must be one of {liana_res.columns}')


def _prep_liana_res(adata=None,
                    liana_res=None,
                    source_labels=None,
                    target_labels=None,
                    ligand_complex=None,
                    receptor_complex=None,
                    uns_key=K.uns_key):

    if (liana_res is None) & (adata is None):
        raise AttributeError(f'Ambiguous! One of `liana_res` or `adata.uns[{uns_key}]` should be provided.')
    if adata is not None:
        assert uns_key in adata.uns.keys()
        liana_res = adata.uns[uns_key].copy()
    if liana_res is not None:
        liana_res = liana_res.copy()
    if (liana_res is None) & (adata is None):
        raise ValueError('`liana_res` or `adata` must be provided!')

    # subset to only cell labels of interest
    liana_res = _filter_labels(liana_res, labels=source_labels, label_type='source')
    liana_res = _filter_labels(liana_res, labels=target_labels, label_type='target')

    liana_res['interaction'] = liana_res['ligand_complex'] + ' -> ' + liana_res['receptor_complex']

    if ligand_complex is not None:
        liana_res = liana_res[np.isin(liana_res['ligand_complex'], ligand_complex)]
    if receptor_complex is not None:
        liana_res = liana_res[np.isin(liana_res['receptor_complex'], receptor_complex)]

    return liana_res


def _filter_labels(liana_res, labels, label_type):
    if labels is not None:
        if labels is str:
            labels = [labels]
        covered = np.isin(labels, liana_res[label_type])
        if not covered.all():
            not_covered = np.array(labels)[~covered]
            raise ValueError(f"{not_covered} not found in `liana_res['{label_type}']`!")
        msk = np.isin(liana_res[label_type], labels)
        liana_res = liana_res[msk]

    return liana_res


def _aggregate_scores(res, what, how, absolute, entities):
    res['score'] = np.absolute(res[what]) if absolute else res[what]
    res = res.groupby(entities).agg(score=('score', how)).reset_index()
    return res


def _inverse_scores(score):
    return -np.log10(score + np.finfo(float).eps)


def _filter_by(liana_res, filterby, filter_lambda):
    if filterby is not None:
        msk = liana_res[filterby].apply(filter_lambda)
        relevant_interactions = np.unique(liana_res[msk].interaction)
        liana_res = liana_res[np.isin(liana_res.interaction, relevant_interactions)]

    return liana_res


def _get_top_n(liana_res, top_n, orderby, orderby_ascending, orderby_absolute):

    if top_n is not None:
        # get the top_n for each interaction
        if orderby is None:
            ValueError("Please specify the column to order the interactions.")
        if orderby_ascending is None:
            ValueError("Please specify if `orderby` is ascending or not.")
        if orderby_ascending:
            how = 'min'
        else:
            how = 'max'

        top_lrs = _aggregate_scores(liana_res,
                                    what=orderby,
                                    how=how,
                                    absolute=orderby_absolute,
                                    entities=['interaction',
                                              'ligand_complex',
                                              'receptor_complex']
                                    ).copy()
        top_lrs = top_lrs.sort_values('score', ascending=orderby_ascending).head(top_n).interaction

        # Filter liana_res to the interactions in top_lrs
        liana_res = liana_res[liana_res['interaction'].isin(top_lrs)]
        # set categories to the order of top_lrs
        liana_res['interaction'] = pd.Categorical(liana_res['interaction'], categories=top_lrs)

    return liana_res
