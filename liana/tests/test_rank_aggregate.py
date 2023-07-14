import pathlib

from unittest import TestCase

from pandas import read_csv
from pandas.testing import assert_frame_equal

from liana.method import rank_aggregate
from liana.method.sc._rank_aggregate import AggregateClass
from liana.testing._toy_adata import get_toy_adata



test_path = pathlib.Path(__file__).parent

adata = get_toy_adata()


def test_consensus():
    assert isinstance(rank_aggregate, AggregateClass)
    assert rank_aggregate.magnitude == 'magnitude_rank'
    assert rank_aggregate.specificity == 'specificity_rank'
    assert rank_aggregate.method_name == 'Rank_Aggregate'


def test_aggregate_specs():
    specificity_specs = {'CellPhoneDB': ('cellphone_pvals', True),
                         'Connectome': ('scaled_weight', False),
                         'log2FC': ('lr_logfc', False),
                         'NATMI': ('spec_weight', False),
                         'CellChat': ('cellchat_pvals', True),
                    }
    TestCase().assertDictEqual(rank_aggregate.specificity_specs, specificity_specs)

    magnitude_specs = {'CellPhoneDB': ('lr_means', False),
                       'Connectome': ('expr_prod', False),
                       'NATMI': ('expr_prod', False),
                       'SingleCellSignalR': ('lrscore', False),
                       'CellChat': ('lr_probs', False)
                       }

    TestCase().assertDictEqual(rank_aggregate.magnitude_specs, magnitude_specs)


def test_aggregate_res():
    lr_res = rank_aggregate(adata, groupby='bulk_labels', use_raw=True, n_perms=2, inplace=False)
    lr_exp = read_csv(test_path.joinpath("data/aggregate_rank_rest.csv"), index_col=0)
    
    assert_frame_equal(lr_res, lr_exp, check_dtype=False, check_exact=False, rtol=1e-4)


def test_aggregate_all():
    rank_aggregate(adata, groupby='bulk_labels', use_raw=True, return_all_lrs=True, key_added='all_res')
    assert adata.uns['all_res'].shape == (4200, 15)


def test_aggregate_by_sample():
    
    rank_aggregate.by_sample(adata, groupby='bulk_labels', use_raw=True, return_all_lrs=True, sample_key='sample', key_added='liana_by_sample')
    lr_by_sample = adata.uns['liana_by_sample']
    
    assert 'sample' in lr_by_sample.columns
    assert lr_by_sample.shape == (10836, 16)
    

def test_aggregate_no_perms():
    rank_aggregate(adata, groupby='bulk_labels', use_raw=True, return_all_lrs=True, key_added='all_res', n_perms=None)
    assert adata.uns['all_res'].shape == (4200, 12)
