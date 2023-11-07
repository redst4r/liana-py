from __future__ import annotations


from docrep import DocstringProcessor

# Common docstrings
_adata = """\
adata
    Annotated data object."""

_mdata = """\
mdata
    MuData (multimodal) data object."""

_misty = """\
misty
    MistyData object with modelling results
"""

_groupby = """\
groupby
    Key to be used for grouping."""

_n_perms = """\
n_perms
    Number of permutations for the permutation test. If None, no p-values are computed."""

_seed = """\
seed
    Random seed for reproducibility."""

_resource = """\
resource
    A pandas dataframe with [`ligand`, `receptor`] columns.
    If provided will overrule the resource requested via `resource_name`"""

_interactions = """\
interactions
    List of tuples with ligand-receptor pairs `[(ligand, receptor), ...]` to be used for the analysis.
    If passed, it will overrule the resource requested via `resource` and `resource_name`."""

_resource_name = """\
resource_name
    Name of the resource to be used for ligand-receptor inference. See `li.rs.show_resources()` for available resources."""

_sample_key = """\
sample_key
    key in `adata.obs` to use for grouping by sample or context."""

_key_added = """\
key_added
    Key under which the results will be stored in `adata.uns` if `inplace` is True."""

_use_raw = """\
use_raw
    Use raw attribute of adata if present."""

_layer = """\
layer
    Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X."""

_mdata_kwargs = """\
mdata_kwargs
    Keyword arguments to be passed to `li.fun.mdata_to_anndata` if `adata` is an instance of `MuData`.
    If an AnnData object is passed, these arguments are ignored."""

_inplace = """\
inplace
    Whether to store results in place, or else to return them."""

_verbose = """\
verbose
    Verbosity flag."""

_lr_sep = """\
lr_sep
    Separator to use when joining ligand and receptor names into interactions.
"""


_source_labels = """\
source_labels
    List of labels to use as `source`, the rest are filtered out.
"""

_target_labels = """\
target_labels
    List of labels to use as `target`, the rest are filtered out.
"""


# Single-cell specific docstrings
_n_perms_sc = """\
n_perms
    Number of permutations for the permutation test. Relevant only for permutation-based methods
    (e.g., `CellPhoneDB`). If `None` is passed, no permutation testing is performed."""

_expr_prop = """\
expr_prop
    Minimum expression proportion for the ligands and receptors (+ their subunits) in the
    corresponding cell identities. Set to 0 to return unfiltered results."""

_min_cells = """\
min_cells
    Minimum cells (per cell identity if grouped by `groupby`) to be considered for downstream analysis."""

_base = """\
base
    Exponent base used to reverse the log-transformation of the matrix. Relevant only for the `logfc` method."""

_return_all_lrs = """\
return_all_lrs
    Bool whether to return all ligand-receptor pairs, or only those that surpass the `expr_prop`
    threshold. Ligand-receptor pairs that do not pass the `expr_prop` threshold will be assigned
    to the *worst* score of the ones that do. `False` by default."""

_de_method = """\
de_method
    Differential expression method. `scanpy.tl.rank_genes_groups` is used to rank genes
    according to 1vsRest. The default method is 't-test'."""


# multi-condition specific docstrings
_source_key = """\
source_key
    Column name of the sender/source cell types in `liana_res`."""

_target_key = """\
target_key
    Column name of the receiver/target cell types in `liana_res`."""

_ligand_key = """\
ligand_key
    Column name of the ligand in `liana_res`."""

_receptor_key = """\
receptor_key
    Column name of the receptor in `liana_res`."""

_score_key = """\
score_key
    Column name of the score in `liana_res`. If None, the score is inferred from the method."""

_uns_key = """\
uns_key
    Key in `adata.uns` that contains the LIANA results. Default is `'liana_res'`."""


_inverse_fun = """\
inverse_fun
    Function that is applied to the scores before building the views. Default is `lambda x: 1 - x` which is used to invert the scores
    reflect probabilities (e.g. magnitude_rank), i.e. such for which lower values reflect higher relevance.
    This is handled automatically for the scores in liana."""


# Spatial specific docstrings
_spatial_key = """\
spatial_key
    Key in `adata.obsm` that contains the spatial coordinates. Default is `'spatial'`."""

_connectivity_key = """\
connectivity_key
    Key in `adata.obsp` that contains the spatial connectivity matrix. Default is `'spatial_connectivity'`. """

_function_name = """\
function_name
    Name of the function to use for the analysis."""

_positive_only = """\
positive_only
    Whether to mask non-positive interactions."""

_add_categories = """\
add_categories
    Whether to add categories about the local scores."""

_x_mod = """\
x_mod
    Name of the modality to use for the x-axis."""

_y_mod = """\
y_mod
    Name of the modality to use for the y-axis."""

_mask_negatives = """\
mask_negatives
    Whether to mask negative-negative (low-low) or uncategorized interactions."""


# Plot docstrings
_liana_res = """\
liana_res
    `liana_res` a `DataFrame` in liana's format.
"""

_colour = """\
colour
    `column` in `liana_res` to define the colours of the dots.
"""

_size = """\
size
    `column` in `liana_res` to define the size of the dots.
"""

_top_n = """\
top_n
    ``top_n`` entities to plot.
"""

_orderby = """\
orderby
    If `top_n` is not `None`, order the interactions by this column
"""

_orderby_ascending = """\
orderby_ascending
    If `top_n` is not `None`, specify how to order the interactions
"""

_orderby_absolute = """\
orderby_absolute
    If `top_n` is not `None`, whether to order by the absolute value of the `orderby` column.
"""

_filterby = """\
filterby
    Column by which to filter the dataframe.
"""

_filter_lambda = """\
filter_lambda
    If `filterby` is not `None`, provide a simple lambda function by which to filter the results to be plotted.
"""

_ligand_complex = """\
ligand_complex
    `list` of ligand complexes to filter the interactions to be plotted. Defaults to None.
"""

_receptor_complex = """\
receptor_complex
    `list` of receptor complexes to filter the interactions to be plotted. Defaults to None.
"""


_inverse_colour = """\
inverse_colour
    Whether to -log10 the `colour` column for plotting. `False` by default.
"""

_inverse_size = """\
inverse_size
    Whether to -log10 the `size` column for plotting. `False` by default.
"""

_size_range = """\
size_range
    Define size range. Tuple of (min, max) integers.
"""

_cmap = """\
cmap
    Colour map to use for plotting.
"""

_figure_size = """\
figure_size
    Figure x,y size
"""

_return_fig = """\
return_fig
    `bool` whether to return the fig object.
"""


d = DocstringProcessor(
    adata=_adata,
    mdata=_mdata,
    misty=_misty,
    groupby=_groupby,
    seed=_seed,
    resource=_resource,
    interactions=_interactions,
    resource_name=_resource_name,
    sample_key=_sample_key,
    key_added=_key_added,
    use_raw=_use_raw,
    layer=_layer,
    mdata_kwargs=_mdata_kwargs,
    inplace=_inplace,
    verbose=_verbose,
    lr_sep=_lr_sep,
    n_perms=_n_perms,
    n_perms_sc=_n_perms_sc,
    expr_prop=_expr_prop,
    min_cells=_min_cells,
    base=_base,
    return_all_lrs=_return_all_lrs,
    liana_res=_liana_res,
    de_method=_de_method,
    source_key=_source_key,
    target_key=_target_key,
    ligand_key=_ligand_key,
    receptor_key=_receptor_key,
    score_key=_score_key,
    uns_key=_uns_key,
    inverse_fun=_inverse_fun,
    spatial_key=_spatial_key,
    connectivity_key=_connectivity_key,
    function_name=_function_name,
    positive_only=_positive_only,
    add_categories=_add_categories,
    x_mod=_x_mod,
    y_mod=_y_mod,
    mask_negatives=_mask_negatives,
    colour=_colour,
    size=_size,
    source_labels=_source_labels,
    target_labels=_target_labels,
    top_n=_top_n,
    orderby=_orderby,
    orderby_ascending=_orderby_ascending,
    orderby_absolute=_orderby_absolute,
    filterby=_filterby,
    filter_lambda=_filter_lambda,
    ligand_complex=_ligand_complex,
    receptor_complex=_receptor_complex,
    inverse_colour=_inverse_colour,
    inverse_size=_inverse_size,
    size_range=_size_range,
    cmap=_cmap,
    figure_size=_figure_size,
    return_fig=_return_fig,

)
