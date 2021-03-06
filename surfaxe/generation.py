
from pymatgen.core.surface import SlabGenerator, generate_all_slabs
from pymatgen import Structure
from pymatgen.io.vasp.sets import DictSet
import warnings
import os

# Monkeypatching straight from Stackoverflow
def custom_formatwarning(message, category, filename, lineno, line=''):
    # Ignore everything except the message
    return 'UserWarning: ' + str(message) + '\n'


PBEsol_slab_config = {
  'INCAR': {'ALGO': 'Normal', 'ADDGRID': False, 'LASPH': True, 'EDIFFG': -0.01,
            'EDIFF': 1e-06, 'ENCUT': 500, 'ISIF': 2, 'ISMEAR': 0, 'GGA': 'PS',
            'LREAL': 'auto', 'LORBIT': 11, 'LCHARG': False, 'LWAVE': False, 
            'NELM': 150, 'NSW': 0, 'PREC': 'Accurate', 'SIGMA': 0.01, 'ISYM': 2, 
            'IWAVPR': 1},
  'KPOINTS': {'reciprocal_density': 90},
  'POTCAR': {'Ac': 'Ac', 'Ag': 'Ag', 'Al': 'Al', 'Ar': 'Ar', 'As': 'As',
             'Au':  'Au', 'B': 'B', 'Ba': 'Ba_sv', 'Be': 'Be_sv', 'Bi': 'Bi',
             'Br': 'Br', 'C': 'C', 'Ca': 'Ca_sv', 'Cd': 'Cd', 'Ce': 'Ce',
             'Cl': 'Cl', 'Co': 'Co', 'Cr': 'Cr_pv', 'Cs': 'Cs_sv', 'Cu': 'Cu',
             'Dy': 'Dy_3', 'Er': 'Er_3', 'Eu': 'Eu', 'F': 'F', 'Fe': 'Fe_pv',
             'Ga': 'Ga_d', 'Gd': 'Gd', 'Ge': 'Ge_d', 'H': 'H', 'He': 'He',
             'Hf': 'Hf_pv', 'Hg': 'Hg', 'Ho': 'Ho_3', 'I': 'I', 'In': 'In_d',
             'Ir': 'Ir', 'K': 'K_sv', 'Kr': 'Kr', 'La': 'La', 'Li': 'Li_sv',
             'Lu': 'Lu_3', 'Mg': 'Mg_pv', 'Mn': 'Mn_pv', 'Mo': 'Mo_pv',
             'N': 'N', 'Na': 'Na_pv', 'Nb': 'Nb_pv', 'Nd': 'Nd_3', 'Ne': 'Ne',
             'Ni': 'Ni_pv', 'Np': 'Np', 'O': 'O', 'Os': 'Os_pv', 'P': 'P',
             'Pa': 'Pa', 'Pb': 'Pb_d', 'Pd': 'Pd', 'Pm': 'Pm_3', 'Pr': 'Pr_3',
             'Pt': 'Pt', 'Pu': 'Pu', 'Rb': 'Rb_sv', 'Re': 'Re_pv',
             'Rh': 'Rh_pv', 'Ru': 'Ru_pv', 'S': 'S', 'Sb': 'Sb', 'Sc': 'Sc_sv',
             'Se': 'Se', 'Si': 'Si', 'Sm': 'Sm_3', 'Sn': 'Sn_d', 'Sr': 'Sr_sv',
             'Ta': 'Ta_pv', 'Tb': 'Tb_3', 'Tc': 'Tc_pv', 'Te': 'Te', 'Th': 'Th',
             'Ti': 'Ti_sv', 'Tl': 'Tl_d', 'Tm': 'Tm_3', 'U': 'U', 'V': 'V_pv',
             'W': 'W', 'Xe': 'Xe', 'Y': 'Y_sv', 'Yb': 'Yb_2', 'Zn': 'Zn',
             'Zr': 'Zr_sv'}}

def get_one_hkl_slabs(structure=None, hkl=None, thicknesses=None, vacuums=None, 
                      make_fols=False, make_input_files=False, max_size=500, 
                      lll_reduce=True, center_slab=True, ox_states=None, 
                      is_symmetric=True, config_dict=PBEsol_slab_config, 
                      potcar_functional='PBE', update_incar=None, 
                      update_kpoints=None, update_potcar=None, **kwargs):
    """
    Generates all unique slabs for a specified Miller index with minimum slab
    and vacuum thicknesses. Note that using this method of slab generation will
    result in different slab index numbers as in the `get_all_slabs` - the slabs
    identified are the same, the index varies based on the position in the list
    of generated slabs

    Args:
        structure (str): filename of structure file in any format supported by
        pymatgen. Default=none, is a required arg.
        hkl (tuple): Miller index; default=None, is a required arg.
        thicknesses (list): minimum size of the slab in angstroms; default=None, 
        is a required arg. 
        vacuums (list): minimum size of the vacuum in angstroms; default=None, 
        is a required arg.
        make_fols (bool): makes folders containing POSCARs; default=False
        make_input_files (bool): makes INCAR, POTCAR and KPOINTS files in each
        of the folders; default=False.
        max_size (int): the maximum number of atoms in the slab for the size
        warning; default=500.
        ox_states (list or dict): add oxidation states either by sites
        i.e. [3, 2, 2, 1, -2, -2, -2, -2] or by element i.e. {'Fe': 3, 'O':-2};
        default=None which adds oxidation states by guess
        is_symmetric (bool): whether or not the slabs cleaved should have 
        inversion symmetry. Needs to be False for slabs cleaved from a
        non-centrosymmetric bulk; default=True
        lll_reduce (bool): whether or not the slabs will be orthogonalized;
        default=True.
        center_slab (bool): position of the slab in the unit cell, if True the
        slab is centered with equal amounts of vacuum above and below; default=True
        config_dict (dict): specifies the dictionary used for generation of
        input files; default=PBEsol_slab_config
        potcar_functional (str): the functional used for POTCAR generation;
        default='PBE'
        update_incar (dict): overrides default INCAR settings; default=None
        update_kpoints (dict or kpoints object): overrides default kpoints
        settings, if supplied as dict should be as {'reciprocal_density': 100};
        default=None
        update_potcar (dict): overrides default POTCAR settings; default=None

    Returns:
        POSCAR_hkl_slab_vac_index.vasp or hkl/slab_vac_index folders with
        POSCARs or hkl/slab_vac_index with all VASP input files
    """
    # Check all neccessary input parameters are present 
    if not any ([structure, hkl, thicknesses, vacuums]): 
        raise ValueError('One or more of the required arguments (structure, '
                         'hkl, thicknesses, vacuums) were not supplied.')
    
    # Import bulk relaxed structure, add oxidation states for slab dipole
    # calculations
    struc = Structure.from_file(structure)
    bulk_name = struc.formula.replace(" ", "")
    struc = oxidation_states(struc, ox_states=ox_states)

    # Iterate through vacuums and thicknessses 
    provisional = []
    for vacuum in vacuums:
        for thickness in thicknesses:
            slabgen = SlabGenerator(struc, hkl, thickness, vacuum,
                                    lll_reduce=lll_reduce,
                                    center_slab=center_slab, **kwargs)
            slabs = slabgen.get_slabs()
            for i, slab in enumerate(slabs):
                # Get all the zero-dipole slabs with inversion symmetry
                if is_symmetric: 
                    if slab.is_symmetric() and not slab.is_polar():
                        provisional.append({'hkl': ''.join(map(str, slab.miller_index)),
                                            'slab_t': thickness,
                                            'vac_t': vacuum,
                                            's_index': i,
                                            'slab': slab})
                
                # Get all the zero-dipole slabs wihtout inversion symmetry
                else: 
                    if not slab.is_polar():
                        provisional.append({'hkl': ''.join(map(str, slab.miller_index)),
                                            'slab_t': thickness,
                                            'vac_t': vacuum,
                                            's_index': i,
                                            'slab': slab})
                  
    # Iterate though provisional slabs to extract the unique slabs
    unique_list, unique_list_of_dicts, repeat, large = ([] for i in range(4))

    for slab in provisional:
        if slab['slab'] not in unique_list:
            unique_list.append(slab['slab'])
            unique_list_of_dicts.append(slab)
            # For large slab size warning
            atoms = len(slab['slab'].atomic_numbers)
            if atoms > max_size:
                large.append('{}_{}_{}_{}'.format(slab['hkl'], slab['slab_t'],
                             slab['vac_t'], slab['s_index']))

        # For repeat slabs warning
        else:
            repeat.append('{}_{}_{}_{}'.format(slab['hkl'], slab['slab_t'],
                          slab['vac_t'], slab['s_index']))

    # Warnings for large and repeated slabs
    if repeat:
        warnings.formatwarning = custom_formatwarning
        warnings.warn('Not all combinations of hkl or slab/vac thicknesses '
        'were generated because of repeat structures. '
        'The repeat slabs are: ' + ', '.join(map(str, repeat)))

    if large:
        warnings.formatwarning = custom_formatwarning
        warnings.warn('Some generated slabs exceed the max size specified.'
        ' Slabs that exceed the max size are: ' + ', '.join(map(str, large)))

    # Makes folders hkl/slab_vac_index, if only make_input_files is true the 
    # folders will also be made automatically. 
    if make_fols or make_input_files:
        for slab in unique_list_of_dicts:
            os.makedirs(os.path.join(os.getcwd(), r'{}/{}_{}_{}'.format(slab['hkl'],
            slab['slab_t'], slab['vac_t'], slab['s_index'])), exist_ok=True)

            # Makes all input files (KPOINTS, POTCAR, INCAR) based on the config
            # dictionary
            if make_input_files:
                vis = DictSet(structure=slab['slab'],
                              config_dict=config_dict,
                              potcar_functional=potcar_functional,
                              user_incar_settings=update_incar,
                              user_potcar_settings=update_potcar,
                              user_kpoints_settings=update_kpoints, **kwargs)
                vis.write_input(r'{}/{}_{}_{}'.format(slab['hkl'],
                                                      slab['slab_t'],
                                                      slab['vac_t'],
                                                      slab['s_index']))

            # Just makes the folders with POSCARs
            else:
                slab['slab'].to(fmt='poscar',
                filename=r'{}/{}_{}_{}/POSCAR'.format(slab['hkl'],
                slab['slab_t'], slab['vac_t'], slab['s_index']))

    # Makes POSCAR_hkl_slab_vac_index files in the bulk_name folder
    else:
        os.makedirs(os.path.join(os.getcwd(), r'{}'.format(bulk_name)),
        exist_ok=True)
        for slab in unique_list_of_dicts:
            slab['slab'].to(fmt='poscar',
            filename=r'{}/POSCAR_{}_{}_{}_{}.vasp'.format(bulk_name,slab['hkl'],
            slab['slab_t'], slab['vac_t'], slab['s_index']))


def get_all_slabs(structure=None, max_index=None, thicknesses=None, 
                  vacuums=None, make_fols=False, make_input_files=False, 
                  max_size=500, ox_states=None, is_symmetric=True, 
                  lll_reduce=True, center_slab=True, 
                  config_dict=PBEsol_slab_config, potcar_functional='PBE', 
                  update_incar=None, update_potcar=None, update_kpoints=None, 
                  **kwargs):
    """
    Generates all unique slabs with specified maximum Miller index, minimum slab
    and vacuum thicknesses. It includes all combinations for multiple zero
    dipole symmetric terminations for the same Miller index. Note that using
    this method of slab generation will results in different slab index numbers
    as in the `get_one_hkl_slabs` - the slabs identified are the same, the index
    varies based on the position in the list of generated slabs.

    Args:
        structure: filename of structure file, takes all pymatgen-supported formats.
        max_index (int): maximum Miller index to be considered
        thicknesses (list): minimum size of the slab in angstroms.
        vacuums (list): minimum size of the vacuum in angstroms.
        make_fols (bool): makes folders containing POSCARs; default=False
        make_input_files (bool): makes INCAR, POTCAR and KPOINTS files in each
        of the folders; if True but make_fols is False it will make the folders 
        regardless; default=False.
        max_size (int): the maximum number of atoms in the slab for the size
        warning; default=500.
        ox_states (list or dict): add oxidation states either by sites
        i.e. [3, 2, 2, 1, -2, -2, -2, -2] or by element i.e. {'Fe': 3, 'O':-2};
        default=None which adds oxidation states by guess
        is_symmetric (bool): whether or not the slabs cleaved should have 
        inversion symmetry. Needs to be False for slabs cleaved from a
        non-centrosymmetric bulk; default=True
        lll_reduce (bool): whether or not the slabs will be orthogonalized;
        default=True.
        center_slab (bool): position of the slab in the unit cell, if True the
        slab is centered with equal amounts of vacuum above and below;
        default=True
        config_dict (dict): specifies the dictionary used for generation of
        input files; default=PBEsol_slab_config
        potcar_functional (str): The functional used for POTCAR generation;
        default='PBE'
        update_incar (dict): overrides default INCAR settings; default=None
        update_kpoints (dict or kpoints object): overrides default kpoints
        settings, if supplied as dict should be as {'reciprocal_density': 100};
        default=None
        update_potcar (dict): overrides default POTCAR settings; default=None

    Returns:
        POSCAR_hkl_slab_vac_index.vasp or hkl/slab_vac_index folders with
        POSCARs or hkl/slab_vac_index with all input files

    """
    # Check all neccessary input parameters are present 
    if not any ([structure, max_index, thicknesses, vacuums]): 
        raise ValueError('One or more of the required arguments (structure, '
                         'max_index, thicknesses, vacuums) were not supplied.')
    
    # Import bulk relaxed structure, add oxidation states for slab dipole
    # calculations
    struc = Structure.from_file(structure)
    bulk_name = struc.formula.replace(" ", "")
    struc = oxidation_states(struc, ox_states=ox_states)
   
    # Iterate through vacuums and thicknessses
    provisional = []
    for vacuum in vacuums:
        for thickness in thicknesses:
            all_slabs = generate_all_slabs(struc, max_index=max_index,
                                        min_slab_size=thickness,
                                        min_vacuum_size=vacuum,
                                        lll_reduce=lll_reduce,
                                        center_slab=center_slab, **kwargs)
            
            for i, slab in enumerate(all_slabs):
                # Get all the zero-dipole slabs with inversion symmetry
                if is_symmetric: 
                    if (slab.is_polar() == False) and (slab.is_symmetric() == True):
                        provisional.append({'hkl': ''.join(map(str, slab.miller_index)),
                                        'slab_t': thickness,
                                        'vac_t': vacuum,
                                        's_index': i,
                                        'slab': slab})
                
                # Get all the zero-dipole slabs wihtout inversion symmetry 
                else: 
                    if not slab.is_polar():
                        provisional.append({'hkl': ''.join(map(str, slab.miller_index)),
                                            'slab_t': thickness,
                                            'vac_t': vacuum,
                                            's_index': i,
                                            'slab': slab})

    # Iterate though provisional slabs to extract the unique slabs
    unique_list, unique_list_of_dicts, repeat, large = ([] for i in range(4))

    for slab in provisional:
        if slab['slab'] not in unique_list:
            unique_list.append(slab['slab'])
            unique_list_of_dicts.append(slab)
            # For large slab size warning
            atoms = len(slab['slab'].atomic_numbers)
            if atoms > max_size:
                large.append('{}_{}_{}_{}'.format(slab['hkl'],
                                                  slab['slab_t'],
                                                  slab['vac_t'],
                                                  slab['s_index']))

        # For repeat slabs warning
        else:
            repeat.append('{}_{}_{}_{}'.format(slab['hkl'],
                                               slab['slab_t'],
                                               slab['vac_t'],
                                               slab['s_index']))

    # Warnings for large and repeated slabs
        if repeat:
            warnings.formatwarning = custom_formatwarning
            warnings.warn('Not all combinations of hkl or slab/vac thicknesses '
            'were generated because of repeat structures. '
            'The repeat slabs are: ' + ', '.join(map(str, repeat)))

        if large:
            warnings.formatwarning = custom_formatwarning
            warnings.warn('Some generated slabs exceed the max size specified.'
            ' Slabs that exceed the max size are: ' + ', '.join(map(str, large)))

    # Makes folders hkl/slab_vac_index, if only make_input_files is true the 
    # folders will also be made automatically.
    if make_fols or make_input_files:
        for slab in unique_list_of_dicts:
            os.makedirs(os.path.join(os.getcwd(), r'{}/{}_{}_{}'.format(slab['hkl'],
            slab['slab_t'], slab['vac_t'], slab['s_index'])), exist_ok=True)

            # Makes all VASP input files (KPOINTS, POTCAR, INCAR) based on the
            # config dictionary
            if make_input_files:
                vis = DictSet(structure=slab['slab'],
                              config_dict=config_dict,
                              potcar_functional=potcar_functional,
                              user_incar_settings=update_incar,
                              user_potcar_settings=update_potcar,
                              user_kpoints_settings=update_kpoints, **kwargs)
                vis.write_input(os.path.join(os.getcwd(), r'{}/{}_{}_{}'.format(slab['hkl'],
                slab['slab_t'], slab['vac_t'], slab['s_index'])))
            
            # Makes the folders with POSCARs
            else:
                slab['slab'].to(fmt='poscar',
                filename=r'{}/{}_{}_{}/POSCAR'.format(slab['hkl'],slab['slab_t'],
                slab['vac_t'], slab['s_index']))

    # Omits folders, makes POSCAR_hkl_slab_vac_index files in folder bulk_name
    else:
        os.makedirs(os.path.join(os.getcwd(), r'{}'.format(bulk_name)),
        exist_ok=True)
        for slab in unique_list_of_dicts:
            slab['slab'].to(fmt='poscar',
            filename='{}/POSCAR_{}_{}_{}_{}.vasp'.format(bulk_name,slab['hkl'],
            slab['slab_t'], slab['vac_t'], slab['s_index']))

def oxidation_states(structure, ox_states=None):
    ''' 
    Args: 
        structure: pymatgen structure object
        ox_states (list or dict): add oxidation states either by sites
        i.e. [3, 2, 2, 1, -2, -2, -2, -2] or by element i.e. {'Fe': 3, 'O':-2};
        default=None which adds oxidation states by guess
    Returns: 
        structure decorated with oxidation states 
    ''' 
    if type(ox_states) is dict:
        structure.add_oxidation_state_by_element(ox_states)
    elif type(ox_states) is list:
        structure.add_oxidation_state_by_site(ox_states)
    else:
        structure.add_oxidation_state_by_guess(max_sites=-1)

    return structure