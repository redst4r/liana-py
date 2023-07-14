Release notes
=============

0.1.9 (06.06.2023)
------------------

- Fixed issues with deprecated params of pandas.DataFrame.to_csv & .assert_frame_equal in tests

- `multi.get_variable_loadings` will now return all factors

- Added source & target params to `fun.generate_lr_geneset`

- Refactored `sc._Method._get_means_perms` & related scoring functions to be more efficient.
 `None` can now be passed to n_perms to avoid permutations - these are only relevant if specificity is assumed to be relevant.

- LIANA's aggregate method can now be customized to include any method of choice (added an example to basic_usage).

- Removed 'Steady' aggregation from rank_aggregate

- Changed deprecated np.float to np.float32 in `liana_pipe`, relevant for CellChat `mat_max`.

- Method results will now be ordered by magnitude, if available, if not specificity is used.

- Added `ligand_complex` and `receptor_complex` filtering to liana's dotplot

- MOFAcellular will now work only with decoupler>=1.4.0 which implements edgeR-like filtering for the views.


0.1.8 (24.03.2023)
------------------

- Removed walrus operator to support Python 3.7

- Added a tutorial that shows the repurposed use of MOFA with liana to obtain intercellular communication programmes, inspired by Tensor-cell2cell

- Added a tutorial that shows the repurposed use of MOFA to the analysis of multicellular programmes as in Ramirez et al., 2023

- Added `key_added` parameter to save liana results to any `adata.uns`` slot, and `uns_key` to use liana results from any `adata.uns` slot

- `inplace` now works as intended (i.e. only writes to `adata.uns` if `inplace` is True).


0.1.7 (08.02.2023)
------------------

- Fixed an edge case where subunits within the same complex with identical values resulted in duplicates. These are now arbitrarily removed according to random order.

- All methods' complexes will now be re-assembled according to the closest stat to expression that each method uses, e.g. `cellchat` will use `trimeans` and the rest `means`.

- Added a basic liana to Tensor-cell2cell tutorial as a solution to liana issue #5

- Updated the basic tutorial 

- Referred to CCC chapter from Theis' best-practices book


0.1.6 (23.01.2023)
-----
- Fixed issue with duplicate subunits for non-expressed LRs when `return_all_lrs` is True

- `min_prop` when working with `return_all_lrs` is now filled with 0s

- Added `by_sample` function to class Method that returns a long-format dataframe of ligand-receptors, for each sample

- Added `dotplot_by_sample` function to visualize ligand-receptor interactions across samples

- Refractored preprocessing of `dotplot` and `dotplot_by_sample` to a separate function

- Changed "pvals" of geometric_mean method to "gmean_pvals" for consistency

- `to_tensor_c2c` utility function to convert a long-format dataframe of ligand-receptor interactions by sample to Tensor-cell2cell tensor.

- Added a list to track the instances of `MethodMeta` class

- Added `generate_lr_geneset` function to generate a geneset of ligand-receptors for different prior knowledge databases


0.1.5 (11.01.2023)
-----
- Hotfix `return_all_lrs` specificity_rank being assigned to NaN

- Add test to check that `specificity_rank` of `lrs_to_keep` is equal to min(specificity_rank)

0.1.4 (11.01.2023)
-----

- `rank_aggregate` will now sort interactions according to `magnitude_rank`.

- Fixed `SettingWithCopyWarning` warning when `return_all_lrs` is True

- Minor text improvements to the basic tutorial notebook

- Removed 'Print' from a verbose print message in `_choose_mtx_rep`


0.1.3 (07.12.2022)
-----
- Added `supp_columns` parameter to allow any column from liana to be returned.

- Added `return_all_lrs` parameter to allow all interactions to be returned with a `lrs_to_filter` flag for the interaction that do not pass the `expr_prop`, and each of those interactions is assigned to the worst **present** score from the ones that do pass the threshold.

- Fixed a bug where an exception was not thrown by `assert_covered`
- Raise explicit exceptions as text in multiple places.

- Changed cellphonedb p-values column name from "pvals" to "cellphone_pvals".

0.1.2
-----
- Added CellChat and GeometricMean methods

0.1.1
-----
- Add progress bar to permutations

- Deal with adata copies to optimize RAM

- change copy to inplace, and assign to uns, rather than return adata

- remove unnecessary filtering in _pre + extend units tests


0.1.0
-----
- Restructure API further

- Submit to PIP


0.0.3
-----
- Added a filter according to `min_cells` per cell identity

- prep_check_adata will now assert that `groupby` exists

- extended test_pre.py tests

- restructured the API to be more scverse-like

0.0.2
-----

- Added `dotplot` as a visualization option

- Added `basic_usage` tutorial

0.0.1
-----

First release alpha version of **liana-py**

- Re-implementations of:
    - CellPhoneDB
    - NATMI
    - SingleCellSignalR
    - Connectome
    - logFC
    - Robust aggregate rank

- Ligand-receptor resources as generated via OmniPathR.

