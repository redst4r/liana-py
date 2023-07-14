from __future__ import annotations

import anndata
import numpy as np
import pandas

from plotnine import ggplot, geom_point, aes, \
    facet_grid, labs, theme_bw, theme, element_text, element_rect, scale_size_continuous


def dotplot(adata: anndata.AnnData = None,
            uns_key = 'liana_res',
            liana_res: pandas.DataFrame = None,
            met: bool = False,
            colour: str = None,
            size: str = None,
            source_labels: list = None,
            target_labels: list = None,
            top_n: int = None,
            orderby: str | None = None,
            orderby_ascending: bool | None = None,
            filterby: bool | None = None,
            filter_lambda=None,
            ligand_complex: str | None = None, 
            receptor_complex: str | None = None,
            inverse_colour: bool = False,
            inverse_size: bool = False,
            size_range: tuple = (2, 9),
            figure_size: tuple = (8, 6),
            return_fig=True) -> ggplot:
    """
    Dotplot interactions by source and target cells

    Parameters
    ----------
    adata
        `AnnData` object with `uns_key` in `adata.uns`. Default is `None`.
    uns_key
        key in adata.uns where liana_res is stored. Defaults to 'liana_res'.
    liana_res
        `liana_res` a `DataFrame` in liana's format
    colour
        `column` in `liana_res` to define the colours of the dots
    size
        `column` in `liana_res` to define the size of the dots
    source_labels
        list to specify `source` identities to plot
    target_labels
        list to specify `target` identities to plot
    top_n
        Obtain only the top_n interactions to plot. Default is `None`
    orderby
        If `top_n` is not `None`, order the interactions by these columns
    orderby_ascending
        If `top_n` is not `None`, specify how to order the interactions
    filterby
        Column by which to filter the interactions
    filter_lambda
        If `filterby` is not `None`, provide a simple lambda function by which
        to filter the interactions to be plotted
    inverse_colour
        Whether to -log10 the `colour` column for plotting. `False` by default.
    inverse_size
        Whether to -log10 the `size` column for plotting. `False` by default.
    size_range
        Define size range - (min, max). Default is (2, 9)
    figure_size
        Figure x,y size
    return_fig
        `bool` whether to return the fig object, `False` only plots

    Returns
    -------
    A `plotnine.ggplot` instance

    """
    liana_res = _prep_liana_res(adata=adata,
                                liana_res=liana_res, 
                                source_labels=source_labels,
                                target_labels=target_labels,
                                ligand_complex = ligand_complex, 
                                receptor_complex = receptor_complex,
                                size=size,
                                colour=colour,
                                uns_key=uns_key
                                ,
                                met=met,)

    if filterby is not None:
        msk = liana_res[filterby].apply(filter_lambda)
        relevant_interactions = np.unique(liana_res[msk].interaction)
        liana_res = liana_res[np.isin(liana_res.interaction, relevant_interactions)]

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

        if met:
            # TODO: get rid of this redundancy
            top_lrs = _aggregate_scores(liana_res, what=orderby, how=how,
                                    entities=['interaction',
                                              'ligand_name',
                                              'receptor']
            )
        else:
            top_lrs = _aggregate_scores(liana_res,
                                    what=orderby,
                                    how=how,
                                    entities=['interaction',
                                              'ligand_complex',
                                              'receptor_complex']
            )
    
        top_lrs = top_lrs.sort_values('score', ascending=orderby_ascending).head(top_n).interaction
        # Filter liana_res to the interactions in top_lrs
        liana_res = liana_res[liana_res.interaction.isin(top_lrs)]
        
    # inverse sc if needed
    if inverse_colour:
        liana_res[colour] = _inverse_scores(liana_res[colour])
    if inverse_size:
        liana_res[size] = _inverse_scores(liana_res[size])

    # generate plot
    p = (ggplot(liana_res, aes(x='target', y='interaction', colour=colour, size=size))
         + geom_point()
         + facet_grid('~source')
         + scale_size_continuous(range=size_range)
         + labs(color=str.capitalize(colour),
                size=str.capitalize(size),
                y="Interactions (Ligand -> Receptor)",
                x="Target",
                title="Source")
         + theme_bw()
         + theme(legend_text=element_text(size=14),
                 strip_background=element_rect(fill="white"),
                 strip_text=element_text(size=15, colour="black"),
                 axis_text_y=element_text(size=10, colour="black"),
                 axis_title_y=element_text(colour="#808080", face="bold", size=15),
                 axis_text_x=element_text(size=11, face="bold", angle=90),
                 figure_size=figure_size,
                 plot_title=element_text(vjust=0, hjust=0.5, face="bold",
                                         colour="#808080", size=15)
                 )
         )

    if return_fig:
        return p

    p.draw()

    
def dotplot_by_sample(adata: anndata.AnnData  = None,
                      uns_key: str = 'liana_res',
                      liana_res: pandas.DataFrame = None,
                      sample_key: str = 'sample',
                      colour: str  = None,
                      size: str = None,
                      inverse_colour: bool = False,
                      inverse_size: bool = False,
                      source_labels: str | None = None,
                      target_labels: str | None = None,
                      ligand_complex: str | None = None, 
                      receptor_complex: str | None = None,
                      size_range: tuple = (2, 9),
                      figure_size: tuple = (8, 6),
                      return_fig: bool = True
                      ):
    """
    A dotplot of interactions by sample
    
    Parameters
    ----------
        adata
            adata object with liana_res and  in adata.uns. Defaults to None.
        uns_key
            key in adata.uns where liana_res is stored. Defaults to 'liana_res'.
        liana_res
            liana_res a DataFrame in liana's format. Defaults to None.
        sample_key
            sample_key used to group different samples/contexts from `liana_res`. Defaults to 'sample'.
        colour
            `column` in `liana_res` to define the colours of the dots. Defaults to None.
        size
            `column` in `liana_res` to define the size of the dots. Defaults to None.
        inverse_colour
            Whether to -log10 the `colour` column for plotting. `False` by default. Defaults to False.
        inverse_size
            Whether to -log10 the `size` column for plotting. `False` by default. Defaults to False.
        source_labels
            `list` with keys as `source` and values as `label` to be used in the plot. Defaults to None.
        target_labels
            `list` with keys as `target` and values as `label` to be used in the plot. Defaults to None.
        ligand_complex
            `list` of ligand complexes to filter the interactions to be plotted. Defaults to None.
        receptor_complex
            `list` of receptor complexes to filter the interactions to be plotted. Defaults to None.
        size_range
            Define size range - (min, max). Default is (2, 9). Defaults to (2, 9).
        figure_size
            Figure x,y size. Defaults to (8, 6).
        return_fig
            `bool` whether to return the fig object, `False` only plots. Defaults to True.
        
    Returns
    -------
    Returns a dotplot of Class ggplot for the specified interactions by sample.
    
    """
    
    liana_res = _prep_liana_res(adata=adata,
                                liana_res=liana_res, 
                                source_labels=source_labels,
                                target_labels=target_labels,
                                ligand_complex=ligand_complex,
                                receptor_complex=receptor_complex,
                                size=size,
                                colour=colour,
                                uns_key=uns_key)    
        
    # inverse sc if needed
    if inverse_colour:
        liana_res[colour] = _inverse_scores(liana_res[colour])
    if inverse_size:
        liana_res[size] = _inverse_scores(liana_res[size])

    p = (ggplot(liana_res, aes(x='target', y='source', colour=colour, size=size))
            + geom_point()
            + facet_grid(f'interaction~{sample_key}', space='free', scales='free')
            + scale_size_continuous(range=size_range)
            + labs(color=str.capitalize(colour),
                   size=str.capitalize(size),
                   y="Source",
                   x="Target",
                   title=sample_key.capitalize())
            + theme_bw()
            + theme(legend_text=element_text(size=14),
                    strip_background=element_rect(fill="white"),
                    strip_text=element_text(size=13, colour="black", angle=90),
                    axis_text_y=element_text(size=10, colour="black"),
                    axis_title_y=element_text(colour="#808080", face="bold", size=12),
                    axis_text_x=element_text(size=11, face="bold", angle=90),
                    axis_title_x=element_text(colour="#808080", face="bold", size=12),
                    figure_size=figure_size,
                    plot_title=element_text(vjust=0, hjust=0.5, face="bold", size=12),
                    )
            )
    if return_fig:
        return p
    
    p.draw()


def _prep_liana_res(adata=None,
                    liana_res=None,
                    source_labels=None,
                    target_labels=None,
                    ligand_complex=None,
                    receptor_complex=None,
                    colour=None,
                    size=None,
                    uns_key='liana_res', 
                    met = False):
    if colour is None:
        raise ValueError('`colour` must be provided!')
    if size is None:
        raise ValueError('`size` must be provided!')
    
    if (liana_res is None) & (adata is None):
        raise AttributeError(f'Ambiguous! One of `liana_res` or `adata.uns[{uns_key}]` should be provided.')
    if adata is not None:
        assert uns_key in adata.uns_keys()
        liana_res = adata.uns[uns_key].copy()
    if liana_res is not None:
        liana_res = liana_res.copy()
    if (liana_res is None) & (adata is None):
        raise ValueError('`liana_res` or `adata` must be provided!')

    # subset to only cell labels of interest
    liana_res = _filter_labels(liana_res, labels=source_labels, label_type='source')
    liana_res = _filter_labels(liana_res, labels=target_labels, label_type='target')
    
    # TODO: Get rid of this redundancy
    if met:
        liana_res['interaction'] = liana_res['ligand_name'] + ' -> ' + liana_res['receptor']
    else:
        liana_res['interaction'] = liana_res['ligand_complex'] + ' -> ' + liana_res['receptor_complex']
    
    if ligand_complex is not None:
        liana_res = liana_res[np.isin(liana_res['ligand_complex'], ligand_complex)]
    if receptor_complex is not None:
        liana_res = liana_res[np.isin(liana_res['receptor_complex'], receptor_complex)]

    return liana_res


def _aggregate_scores(res, what, how, entities):
    return res.groupby(entities).agg(score=(what, how)).reset_index()


def _inverse_scores(score):
    return -np.log10(score + np.finfo(float).eps)


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
        