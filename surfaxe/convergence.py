# Pymatgen
from pymatgen.core.surface import Slab
from pymatgen import Structure, Specie, Element
from pymatgen.core.sites import PeriodicSite
from pymatgen.io.vasp.outputs import Vasprun

# Misc
import os
import math
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('once')

# Matplotlib
import matplotlib as mpl
from matplotlib import pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
mpl.rcParams.update({'font.size': 14})


def slab_from_file(structure, hkl):
    """
    Reads in structure from the file and returns slab object.

    Args:
         structure (str): structure file in any format supported by pymatgen
         hkl (tuple): Miller index of the slab in the input file.

    Returns:
         Slab object
    """
    slab_input = Structure.from_file(structure)
    return Slab(slab_input.lattice,
                slab_input.species_and_occu,
                slab_input.frac_coords,
                hkl,
                Structure.from_sites(slab_input, to_unit_cell=True),
                shift=0,
                scale_factor=np.eye(3, dtype=np.int),
                site_properties=slab_input.site_properties)

def parse_fols(hkl=None, bulk_per_atom=None, **kwargs):
    """
    Parses the convergence folders to get the surface energy, total energy,
    energy per atom and time taken for each slab and vacuum thickness
    combination

    Args:
        hkl (tuple): Miller index of the slab
        bulk_per_atom (float): bulk energy per atom from a converged bulk
        calculation

    Returns:
        hkl_data.csv
    """
     # Check all neccessary input parameters are present 
    if not any ([hkl, bulk_per_atom]): 
        raise ValueError('One or more of the required arguments (bulk_per_atom, '
                         'hkl) were not supplied.')

    df_list = []
    hkl_sorted = ''.join(map(str, hkl))

    for root, fols in os.walk('.'):
        for fol in fols:
            if not any([fol==root, fol=='.ipynb_checkpoints']):
                path = os.path.join(root, fol)
                vsp_path = '{}/vasprun.xml'.format(path)

                # instantiate structure, slab and vasprun objects
                vsp = Vasprun(vsp_path, **kwargs)
                slab = slab_from_file(vsp_path, hkl)
                vsp_dict = vsp.as_dict()

                # extract the data
                area = slab.surface_area
                atoms = vsp_dict['nsites']
                slab_energy = vsp.final_energy
                energy_per_atom = slab_energy / atoms
                surface_energy = (slab_energy - bulk_per_atom * atoms)/(2 * area) * 16.02

                # name of fol has to be ./slabthickness_vacthickness_index
                slab_vac_index = fol.split('_')

                # reads the outcar to get the time taken
                with open('{}/OUTCAR'.format(path), 'r') as otc:
                    lines = list(otc)
                    line = lines[-8].split(':')

                df_list.append({'slab_thickness': slab_vac_index[0],
                          'vac_thickness': slab_vac_index[1],
                          'slab_index': slab_vac_index[2],
                          'surface_energy': surface_energy,
                          'slab_toten': slab_energy,
                          'slab_per_atom': energy_per_atom,
                          'time_taken': line[1].strip()})

    df = pd.DataFrame(df_list)
    df.to_csv('{}_data.csv'.format(hkl_sorted), index=False)

def plot_surfen(hkl=None, time_taken=True, cmap='Wistia', fmt='png', dpi=300, **kwargs):
    """
    Reads from the csv file created by `parse_fols` to plot the surface energy
    for all possible terminations

    Args:
        hkl (tuple): Miller index
        time_taken (bool): whether it shows the time taken for calculation to
        finish on the graph; default=True
        cmap (str): Matplotlib colourmap; defaut='Wistia'
        fmt (str): format for the output file; default='png'
        dpi (int): dots per inch; default=300

    Returns:
        hkl_surface_energy.png
    """
    # Check all neccessary input parameters are present 
    if not hkl: 
        raise ValueError('The required argument hkl was not supplied')

    hkl_sorted = ''.join(map(str, hkl))
    df = pd.read_csv('{}_data.csv'.format(hkl_sorted))

    indices, vals, times, dfs = ([] for i in range(4))

    # Group the values by termination slab index, create df for time and
    # energy values. Converts the energy and time values to np arrays for plotting
    for group in df.groupby('slab_index'):
        df2 = group[1].pivot(index='slab_thickness',
                             columns='vac_thickness',
                             values='surface_energy')
        df3 = group[1].pivot(index='slab_thickness',
                             columns='vac_thickness',
                             values='time_taken')
        indices.append(group[0])
        vals.append(df2.to_numpy())
        times.append(df3.to_numpy())
        dfs.append(df2)

    # Plotting has to be separated into plotting for one and more than one
    # indices mpl won't let you index axes if there's only one set
    if len(indices) == 1:
        mpl.rcParams['figure.figsize'] = (6.0,6.0)
        fig, ax = plt.subplots(1,1)
        ax.set_title('{} surface energies'.format(hkl))

        for (index, val, time, df) in zip(indices, vals, times, dfs):
            ax.set_yticks(list(range(len(df.index))))
            ax.set_yticklabels(df.index)
            ax.set_ylabel('Slab thickness')
            ax.set_xticks(list(range(len(df.columns))))
            ax.set_xticklabels(df.columns)
            ax.set_xlabel('Vacuum thickness')
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.2)
            im = ax.imshow(val, cmap=cmap)
            fig.colorbar(im, cax=cax, orientation='vertical')
            ax.invert_yaxis()

        # Add the surface energy value labels to the plot - the for loops are
        # needed in this order and they can't be zipped because this is the
        # only way they display the values correctly
        for df in dfs:
            for j in range(len(df.index)):
                for k in range(len(df.columns)):
                    for val in vals:
                        ax.text(k, j, f"{val[j, k]: .3f}", ha="center",
                                          va="bottom", color="black")

        # Add the time taken labels to the plot
        if time_taken:
            for df in dfs:
                for j in range(len(df.index)):
                    for k in range(len(df.columns)):
                        for time in times:
                            ax.text(k, j, (f"{time[j, k]: .0f}"+' s'),
                                              ha="center", va="top", color="black")

    # Plotting for multiple indices
    else:
        mpl.rcParams['figure.figsize'] = (10.0,10.0)
        fig, ax = plt.subplots(ncols=len(indices))

        # The extra args are there because the default leaves a massive gap
        # between the title and subplot titles, no amount of changing tight_layout
        # and subplots_adjust helped with the issue - this is a known mpl issue
        fig.suptitle('{} surface energies'.format(hkl), y=0.73, ha='center',
                     va='top', size=22)

        # Iterate through the values for plotting, create each plot on a separate 
        # ax, add the colourbar to each ax
        for i, (index, val, time, df) in enumerate(zip(indices, vals, times, dfs)):
            ax[i].set_title('Slab index {}'.format(index))
            ax[i].set_yticks(list(range(len(df.index))))
            ax[i].set_yticklabels(df.index)
            ax[i].set_ylabel('Slab thickness')
            ax[i].set_xticks(list(range(len(df.columns))))
            ax[i].set_xticklabels(df.columns)
            ax[i].set_xlabel('Vacuum thickness')
            im = ax[i].imshow(val, cmap=cmap)
            divider = make_axes_locatable(ax[i])
            cax = divider.append_axes("right", size="5%", pad=0.2)
            plt.colorbar(im, cax=cax)
            ax[i].invert_yaxis()
        fig.tight_layout()

        # Add the surface energy value labels to the plot
        for df in dfs:
            for j in range(len(df.index)):
                for k in range(len(df.columns)):
                    for i, val in enumerate(vals):
                        ax[i].text(k, j, f"{val[j, k]: .3f}", ha="center",
                                          va="bottom", color="black")

        # Add the time taken labels to the plot
        if time_taken:
            for df in dfs:
                for j in range(len(df.index)):
                    for k in range(len(df.columns)):
                        for i, time in enumerate(times):
                            ax[i].text(k, j, (f"{time[j, k]: .0f}"+' s'),
                                              ha="center", va="top", color="black")


    plt.savefig('{}_surface_energy.{}'.format(''.join(map(str, hkl)), fmt),
    dpi=dpi, bbox_inches='tight', **kwargs)


def plot_enatom(hkl=None, time_taken=True, cmap='Wistia', fmt='png', dpi=300, **kwargs):
    """
    Reads from the csv file created by `parse_fols` to plot the energy per atom
    for all possible terminations

    Args:
        hkl (tuple): Miller index
        time_taken (bool): whether it shows the time taken for calculation to
        finish on the graph; default=True
        cmap (str): Matplotlib colourmap used; defaut='Wistia'
        fmt (str): format for the output file; default='png'
        dpi (int): dots per inch; default=300

    Returns:
        hkl_energy_per_atom.png
    """
    # Check all neccessary input parameters are present 
    if not hkl: 
        raise ValueError('The required argument hkl was not supplied') 

    hkl_sorted = ''.join(map(str, hkl))
    df = pd.read_csv('{}_data.csv'.format(hkl_sorted))

    indices, vals, times, dfs = ([] for i in range(4))

    # Group the values by termination slab index, create df for time and
    # energy values. Converts the energy and time values to np arrays for plotting
    for group in df.groupby('slab_index'):
        df2 = group[1].pivot(index='slab_thickness',
                             columns='vac_thickness',
                             values='slab_per_atom')
        df3 = group[1].pivot(index='slab_thickness',
                             columns='vac_thickness',
                             values='time_taken')
        indices.append(group[0])
        vals.append(df2.to_numpy())
        times.append(df3.to_numpy())
        dfs.append(df2)

    if len(indices) == 1:
        mpl.rcParams['figure.figsize'] = (6.0,6.0)
        fig, ax = plt.subplots(1,1)
        ax.set_title('{} energies per atom'.format(hkl))

        # Iterate through the values for plotting, create each plot on a separate ax,
        # add the colourbar to each ax
        for index, val, time, df in zip(indices, vals, times, dfs):
            ax.set_yticks(list(range(len(df.index))))
            ax.set_yticklabels(df.index)
            ax.set_ylabel('Slab thickness')
            ax.set_xticks(list(range(len(df.columns))))
            ax.set_xticklabels(df.columns)
            ax.set_xlabel('Vacuum thickness')
            im = ax.imshow(val, cmap=cmap)
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.2)
            plt.colorbar(im, cax=cax)
            ax.invert_yaxis()

        # Add the surface energy value labels to the plot, the for loop have to
        # be in this order becuase it breaks the text if i and val are in the
        # first loop, also j and k can't be zipped
        for df in dfs:
            for j in range(len(df.index)):
                for k in range(len(df.columns)):
                    for val in vals:
                        ax.text(k, j, f"{val[j, k]: .3f}", ha="center",
                                          va="bottom", color="black")

        # Add the time taken labels to the plot, same loop comment as above
        if time_taken:
            for df in dfs:
                for j in range(len(df.index)):
                    for k in range(len(df.columns)):
                        for time in times:
                            ax.text(k, j, (f"{time[j, k]: .0f}"+' s'),
                                              ha="center", va="top", color="black")

    # Plotting for multiple indices
    else:
        mpl.rcParams['figure.figsize'] = (10.0,10.0)
        fig, ax = plt.subplots(ncols=len(indices))

        # The extra args are there because the default leaves a massive gap
        # between the title and subplot titles, no amount of changing tight_layout
        # and subplots_adjust helped with the issue
        fig.suptitle('{} energies per atom'.format(hkl), y=0.73, ha='center',
                     va='top', size=22)

        # Iterate through the values for plotting, create each plot on a separate ax,
        # add the colourbar to each ax
        for i, (index, val, time, df) in enumerate(zip(indices, vals, times, dfs)):
            ax[i].set_title('Slab index {}'.format(index))
            ax[i].set_yticks(list(range(len(df.index))))
            ax[i].set_yticklabels(df.index)
            ax[i].set_ylabel('Slab thickness')
            ax[i].set_xticks(list(range(len(df.columns))))
            ax[i].set_xticklabels(df.columns)
            ax[i].set_xlabel('Vacuum thickness')
            im = ax[i].imshow(val, cmap=cmap)
            divider = make_axes_locatable(ax[i])
            cax = divider.append_axes("right", size="5%", pad=0.2)
            plt.colorbar(im, cax=cax)
            ax[i].invert_yaxis()
        fig.tight_layout()

        # Add the surface energy value labels to the plot, the for loop have to
        # be in this order becuase it breaks the text if i and val are in the
        # first loop, also j and k can't be zipped
        for df in dfs:
            for j in range(len(df.index)):
                for k in range(len(df.columns)):
                    for i, val in enumerate(vals):
                        ax[i].text(k, j, f"{val[j, k]: .3f}", ha="center",
                                          va="bottom", color="black")

        # Add the time taken labels to the plot, same loop comment as above
        if time_taken:
            for df in dfs:
                for j in range(len(df.index)):
                    for k in range(len(df.columns)):
                        for i, time in enumerate(times):
                            ax[i].text(k, j, (f"{time[j, k]: .0f}"+' s'),
                                              ha="center", va="top", color="black")


    plt.savefig('{}_energy_per_atom.{}'.format(''.join(map(str, hkl)),fmt),
    dpi=dpi, bbox_inches='tight', **kwargs)
