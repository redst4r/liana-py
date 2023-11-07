import pathlib
from scanpy.datasets import pbmc68k_reduced
from pandas.testing import assert_frame_equal
from pandas import read_csv
import numpy as np

from liana.method.sc._liana_pipe import liana_pipe, _expm1_base, _calc_log2fc
from liana._constants import DefaultValues as V

test_path = pathlib.Path(__file__).parent
adata = pbmc68k_reduced()

groupby = 'bulk_labels'

# Test ALL Default parameters
def test_liana_pipe_defaults():
    all_defaults = liana_pipe(adata=adata,
                              groupby=groupby,
                              resource_name=V.resource_name,
                              expr_prop=V.expr_prop,
                              min_cells=V.min_cells,
                              de_method=V.de_method,
                              base=V.logbase,
                              n_perms=V.n_perms,
                              seed=V.seed,
                              verbose=V.seed,
                              supp_columns=[],
                              resource=V.resource,
                              use_raw=V.use_raw,
                              layer=V.layer,
                              interactions=V.interactions,
                              )

    assert 1288 == all_defaults.shape[0]
    assert 21 == all_defaults.shape[1]
    assert 'prop_min' in all_defaults.columns

    exp_defaults = read_csv(test_path.joinpath("data", "all_defaults.csv"), index_col=0)
    exp_defaults.index = all_defaults.index
    assert_frame_equal(all_defaults, exp_defaults, check_dtype=False,
                       check_exact=False, check_index_type=False, rtol=1e-3)


# Test NOT Default parameters
def test_liana_pipe_not_defaults():
    not_defaults = liana_pipe(adata=adata,
                              groupby=groupby,
                              resource_name=V.resource_name,
                              expr_prop=0.2,
                              min_cells=V.min_cells,
                              de_method='wilcoxon',
                              base=V.logbase,
                              n_perms=V.n_perms,
                              seed=V.seed,
                              verbose=V.verbose,
                              supp_columns=['ligand_pvals', 'receptor_pvals'],
                              resource=V.resource,
                              use_raw=V.use_raw,
                              layer=V.layer,
                              return_all_lrs=True,
                              interactions=V.interactions,
                              )

    assert 4200 == not_defaults.shape[0]
    assert 24 == not_defaults.shape[1]
    assert all(np.isin(['lrs_to_keep'], not_defaults.columns))
    assert all(np.isin(['ligand_pvals', 'receptor_pvals'], not_defaults.columns))

    exp_defaults = read_csv(test_path.joinpath("data/not_defaults.csv"), index_col=0)
    exp_defaults.index = not_defaults.index
    assert_frame_equal(not_defaults, exp_defaults, check_dtype=False,
                       check_index_type=False, check_exact=False, rtol=1e-3)


def test_expm1_fun():
    expm1_mat = _expm1_base(V.logbase, adata.raw.X.data)
    np.testing.assert_almost_equal(np.sum(expm1_mat), 1057526.4, decimal=1)


def test_calc_log2fc():
    adata.layers['normcounts'] = adata.raw.X.copy()
    adata.layers['normcounts'].data = _expm1_base(V.logbase, adata.raw.X.data)
    adata.obs['@label'] = adata.obs.bulk_labels
    np.testing.assert_almost_equal(np.mean(_calc_log2fc(adata, "Dendritic")), -0.123781264)
