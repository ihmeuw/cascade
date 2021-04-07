#!/usr/bin/env python
# ------------------------------------------------------------------------

import sys
import pandas as pd
import numpy as np
import shutil

from collections import OrderedDict
from cascade_at.executor.init_no_ode import init_ode_command, fit_ode_command, fit_students_command

__check__ = True

def parse_args(args):
    import argparse
    from distutils.util import strtobool as str2bool
    parser = argparse.ArgumentParser()

    parser.add_argument('cmd', type=str, help='An extended dmdismod command, to handle the ODE_init and ODE_students fit strategies.')
    parser.add_argument('path', type=str, help='Path to the Dismod_AT sqlite database')
    parser.add_argument('dispatch', type=str, help='Switch to switch to ODE strategy')
    parser.add_argument('option', type=str, help='One of ODE_fit or ODE_students. Everything else is passed directly on to the regular dmdismod command.')

    parser.add_argument("-m", "--max-covariate-effect", nargs='?', type=float, default = 2,
                        help = ("Maximum absolute covariate effect = multiplier * (covariate - referece). "
                                "Note that exp(effect) multiplies a model value to get the model value for "
                                "this covariate value. (Noise covariate multipliers are not included.)"))
    parser.add_argument("-c", '--mulcov-values', nargs='+', type=str, default = None,
                        help = "Constrain covariate multipliers to the specified value")
    parser.add_argument("-o", "--ode-hold-out-list", nargs='?', type=str, default = None, const = None,
                        help = "Integrands to hold out during the ODE fit") 
    parser.add_argument("-s", "--random-seed", nargs='?', type=int, default = None,
                        help = "Random seed for the random_subsampling") 
    parser.add_argument("-f", "--subset", nargs='?', type=str2bool, default = False, const = False,
                        help = "Filter out all hold out and covariate out-of-range data prior to fit.")
    parser.add_argument("-d", "--random-subsample", nargs='?', type=int, default = 1000, const = None,
                        help = "Number of random subsamples to fit.")
    parser.add_argument("-p", "--save-to-path", nargs='?', type=str, default = None, const = None,
                        help = "Path to directory where to store the results") 
    parser.add_argument("-t", "--reference_db", nargs='?', type=str, default = "", const = "",
                        help = "Path to the reference databases. Fit results are compared to these databases for testing purposes.")

    get_help = len(args) > 1 and any(a.startswith('-h') for a in args[1:])
    if get_help:
        args = parser.parse_args(args[1:])
    else:
        args = parser.parse_args(args)
    if args.mulcov_values is None:
        args.mulcov_values = []
    else:
        args.mulcov_values = [[a,b,float(c)] for a,b,c in np.asarray(args.mulcov_values).reshape(-1, 3)]
    return args

def dmdismod(cmd):
    args = cmd.split()
    p_args = parse_args(cmd.split())
    print ('-'*10)
    print (cmd)
    print ('-'*10)
    
    if p_args.option == "init":
        db = init_ode_command(['dismod_at'] + args[1:], 
                              max_covariate_effect = p_args.max_covariate_effect,
                              mulcov_values = p_args.mulcov_values,
                              ode_hold_out_list = p_args.ode_hold_out_list,
                              random_seed = p_args.random_seed,
                              subset = p_args.subset,
                              random_subsample = p_args.random_subsample,
                              save_to_path = p_args.save_to_path,
                              reference_db = p_args.reference_db)
    elif p_args.option == "fit":
        db = fit_ode_command(['dismod_at'] + args[1:],
                             ode_hold_out_list = p_args.ode_hold_out_list,
                             random_seed = p_args.random_seed,
                             subset = p_args.subset,
                             random_subsample = p_args.random_subsample,
                             save_to_path = p_args.save_to_path,
                             reference_db = p_args.reference_db)
    elif p_args.option == "students":
        fit_students_command(['dismod_at'] + args[1:],
                             ode_hold_out_list = p_args.ode_hold_out_list,
                             subset = p_args.subset,
                             random_seed = p_args.random_seed,
                             random_subsample = p_args.random_subsample,
                             save_to_path = p_args.save_to_path,
                             reference_db = p_args.reference_db)

if __name__ == '__main__':

    def test():
        def test_args(cmd, disease):
            dispatch = {'init': 'no_ode',
                        'fit': 'yes_ode',
                        'students': 'students'} 
            path = cmd.split()[1]
            type = dispatch[cmd.split()[3]]
            save_path = path.replace('.db', f'_{type}.db')
            arg_str = (f" --random-seed 1234 --subset True --random-subsample 1000"
                       f" --save-to-path {save_path}"
                       f" --reference /Users/gma/ihme/epi/at_cascade/{disease}/{type}/{type}.db")
            return arg_str

        paths = dict( crohns = '/Users/gma/ihme/epi/at_cascade/data/475533/dbs/1/2/dismod.db',
                      dialysis = '/Users/gma/ihme/epi/at_cascade/data/475527/dbs/96/2/dismod.db', # S Latin America
                      # dialysis = '/Users/gma/ihme/epi/at_cascade/data/475527/dbs/1/2/dismod.db',  # Global
                      kidney = '/Users/gma/ihme/epi/at_cascade/data/475718/dbs/70/1/dismod.db',
                      osteo_hip =  '/Users/gma/ihme/epi/at_cascade/data/475526/dbs/1/2/dismod.db',
                      # osteo_hip_world = '/Users/gma/ihme/epi/at_cascade/data/475745/dbs/1/2/dismod.db',
                      osteo_knee = '/Users/gma/ihme/epi/at_cascade/data/475746/dbs/64/2/dismod.db',
                      # t1_diabetes =  '/Users/gma/ihme/epi/at_cascade/data/475882/dbs/1/2/dismod.db', # world
                      # t1_diabetes =  '/Users/gma/ihme/epi/at_cascade/data/475882/dbs/100/2/dismod.db', # HI N America female
                      t1_diabetes = '/Users/gma/ihme/epi/at_cascade/data/475588/dbs/100/3/dismod.db', # HI N America both
                      )

        cmds = OrderedDict(t1_diabetes = ['dismod_at /tmp/t1_diabetes.db ODE init',
                                          'dismod_at /tmp/t1_diabetes.db ODE fit --ode-hold-out-list mtexcess',
                                          'dismod_at /tmp/t1_diabetes.db ODE students --ode-hold-out-list mtexcess'],
                           dialysis = ['dismod_at /tmp/dialysis.db ODE init --max-covariate-effect 4',
                                       'dismod_at /tmp/dialysis.db ODE fit --max-covariate-effect 4',
                                       'dismod_at /tmp/dialysis.db ODE students --max-covariate-effect 4'],
                           kidney = ['dismod_at /tmp/kidney.db ODE init',
                                     'dismod_at /tmp/kidney.db ODE fit',
                                     'dismod_at /tmp/kidney.db ODE students'],
                           osteo_hip = ['dismod_at /tmp/osteo_hip.db ODE init',
                                        'dismod_at /tmp/osteo_hip.db ODE fit',
                                        'dismod_at /tmp/osteo_hip.db ODE students'],
                           osteo_knee = ['dismod_at /tmp/osteo_knee.db ODE init',
                                         'dismod_at /tmp/osteo_knee.db ODE fit',
                                         'dismod_at /tmp/osteo_knee.db ODE students'],
                           crohns = ['dismod_at /tmp/crohns.db ODE init --mulcov-values x_0 iota 3.8661',
                                     'dismod_at /tmp/crohns.db ODE fit --mulcov-values x_0 iota 3.8661',
                                     'dismod_at /tmp/crohns.db ODE students --mulcov-values x_0 iota 3.8661'],
                    )


        for disease,_cmds in cmds.items():
            path_in = paths[disease]
            path_fit = f'/tmp/{disease}.db'
            print (f'Copying {path_in} to {path_fit} for testing.')
            shutil.copy2(path_in, path_fit)
            for cmd in _cmds:
                dispatch = {'init': 'no_ode',
                            'fit': 'yes_ode',
                            'students': 'students'} 
                if __check__:
                    cmd += test_args(cmd, disease)

                print (cmd)

                dmdismod(cmd)


    if sys.argv[0]:
        cmd = ' '.join(sys.argv)
        print (cmd)
        dmdismod(cmd)
    else:
        test()

"""
dmdismod('dismod_at /tmp/t1_diabetes.db ODE init')
dmdismod('dismod_at /tmp/t1_diabetes.db ODE fit --ode-hold-out-list mtexcess')
dmdismod('dismod_at /tmp/t1_diabetes.db ODE students --ode-hold-out-list mtexcess')
"""