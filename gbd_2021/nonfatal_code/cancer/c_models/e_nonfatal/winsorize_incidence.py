'''
Name: winsorize_incidence.py
Description: For locations in high-income super region, compile all HIC locations and winsorizes data based on 95% cap
    NOTE: the caps are generated and applied to to only high-income countries, and not all locations. This module should only be ran 
    if all HICs locations have incidence draws generated 
Contributors: USERNAME 
'''

# import libraries 
import pdb 
import os
import numpy as np 
import pandas as pd
from scipy.stats import mstats
import cancer_estimation.c_models.e_nonfatal.nonfatal_dataset as nd
import cancer_estimation.py_utils.common_utils as utils 


def get_nf_hic_locations() -> list:
    ''' Returns list of high-income locations present in NF modeling 
    '''
    loc_df = pd.read_csv('{}/location_metadata.csv'.format(utils.get_path(process='nonfatal_model', key='database_cache')))
    hics = loc_df.loc[loc_df['super_region_name'].eq('High-income'), 'location_id'].unique().tolist() 

    nf_locations = nd.list_location_ids() 

    # return the intersection of locations 
    hic_nf_locs = set(hics) & set(nf_locations) 
    return list(hic_nf_locs)


def agg_and_create_rates() -> None:
    ''' for high-income locations only - 
        loads incidence file; aggregates and creates < 5 age-group; appends rows of rates data; exports 
    ''' 
    keepcols = ['year_id','sex_id','age_group_id','location_id','acause','mean','metric_id']
    tmpdir =  '{}/neo_eye_rb'.format(utils.get_path(process='nonfatal_model', key='incidence_temp_draws'))
    indir = '{}/neo_eye_rb/pre_winsorize'.format(utils.get_path(process='nonfatal_model', key='incidence_temp_draws')) 
    pop_df = pd.read_csv('{}/population.csv'.format(utils.get_path(process='nonfatal_model', key='database_cache')))
    inc_draws = ['inc_{}'.format(i) for i in range(0,1000)]

    # compile high-income incidence draws 
    hics = get_nf_hic_locations() 
    count_inc = pd.concat([pd.read_csv('{}/{}.csv'.format(indir, l)) for l in hics])

    # calculate original sum 
    orig_sum_df = count_inc.copy(deep=True)
    orig_sum_df['mean'] = orig_sum_df[inc_draws].mean(axis=1)
    orig_sum = orig_sum_df['mean'].sum() 

    # aggregate < 5 years 
    count_inc.loc[~count_inc['age_group_id'].eq(6), 'age_group_id'] = 1 
    count_inc = count_inc.groupby(by=['year_id','sex_id','age_group_id','location_id','acause'])[inc_draws].sum().reset_index()
    count_inc['metric_id'] = 1 

    # create rates df  
    rate_inc = count_inc.copy(deep=True)
    rate_inc = pd.merge(rate_inc, pop_df, on=['location_id','age_group_id','sex_id','year_id'], how='left')
    for i in inc_draws: 
        rate_inc[i] = rate_inc[i] / rate_inc['population']
    rate_inc['metric_id'] = 3 # rates 

    # summary of count and rate draws 
    count_inc['mean'] = count_inc[inc_draws].mean(axis=1)
    rate_inc['mean'] = rate_inc[inc_draws].mean(axis=1)
    
    assert (np.isclose(orig_sum, count_inc['mean'].sum()))
    assert (rate_inc['mean'] < 1).all()
    tmp_inc = count_inc.append(rate_inc)

    # keep only rates 
    all_rates = tmp_inc.loc[tmp_inc['metric_id'].eq(3), ] 
    return all_rates[keepcols]


def create_caps(hic_df : pd.DataFrame) -> tuple: 
    ''' Takes a dataframe and calculates 95% caps and returns a tuple of dataframes
    '''
    # calculate caps for < 5 age group 
    cap_age1 = hic_df.loc[hic_df['age_group_id'].eq(1), 'mean'].quantile([0.025, 0.975]).reset_index()
    cap_age1['cap_age_group_id'] = 1 
    cap_age1.rename(columns={'index' : 'quantile',
                            'mean':'cap'}, inplace=True)
    
    # calculate caps for 5-9 age group 
    cap_age6 = hic_df.loc[hic_df['age_group_id'].eq(6), 'mean'].quantile([0.025, 0.975]).reset_index() 
    cap_age6['cap_age_group_id'] = 6 
    cap_age6.rename(columns={'index' : 'quantile',
                            'mean' :'cap'}, inplace=True)
    cap_df = cap_age1.append(cap_age6)

    # separate cap data for later merge 
    upper_caps = cap_df.loc[cap_df['quantile'].eq(0.975), ]
    upper_caps.rename(columns={'cap':'upper_cap_rate'}, inplace=True)
    lower_caps = cap_df.loc[cap_df['quantile'].eq(0.025), ]
    lower_caps.rename(columns={'cap': 'lower_cap_rate'}, inplace=True)

    # export caps 
    return(upper_caps, lower_caps) 


def main(location_id : int) -> None: 
    ''' Compiles NF incidence results, calculates caps based on all NF locations
        Then winsorizes draw data based on caps which were in rates 
    '''
    outdir = utils.get_path(process='nonfatal_model', key='incidence_draws_output')
    keep_cols = ['year_id','sex_id','age_group_id','location_id','acause']
    pop_df = pd.read_csv('{}/population.csv'.format(utils.get_path(process='nonfatal_model', key='database_cache')))
    inc_draws = ['inc_{}'.format(i) for i in range(0,1000)]

    # compile mean results 
    rate_df = agg_and_create_rates() 

    # calculate upper and lower caps by age-group, metric
    (upper_caps, lower_caps) = create_caps(rate_df) 
  
    # apply caps if the location is high-income 
    hic_locs = get_nf_hic_locations() 
    if location_id in hic_locs:
        print('applying caps for HICs...')
        # load data 
        df_input = pd.read_csv('{}/neo_eye_rb/pre_winsorize/{}.csv'.format(utils.get_path(process='nonfatal_model',
                                                                                          key='incidence_temp_draws'),
                                                                           location_id))
        df_input.loc[~df_input['age_group_id'].eq(6), 'cap_age_group_id'] = 1
        df_input.loc[df_input['age_group_id'].eq(6), 'cap_age_group_id'] = 6

        # merge caps and population 
        df = pd.merge(df_input, lower_caps, on='cap_age_group_id', how='left')
        df = pd.merge(df, upper_caps, on='cap_age_group_id', how='left')
        df = pd.merge(df, pop_df, on=['age_group_id','sex_id','year_id','location_id'], how='left')

        # for each draw, apply cap 
        for d in inc_draws:
            # conditions for when to apply caps
            app_low_cap_cond = df[d] < (df['lower_cap_rate'] * df['population'])
            app_upper_cap_cond = df[d] > (df['upper_cap_rate'] * df['population'])
            
            # apply lower_cap  
            df.loc[app_low_cap_cond, d] = df['lower_cap_rate'] * df['population']
            df.loc[app_low_cap_cond, 'below_lower_cap'] = 1 
            
            # apply upper cap 
            df.loc[app_upper_cap_cond, d] = df['upper_cap_rate'] * df['population']
            df.loc[app_upper_cap_cond, 'above_upper_cap'] = 1  
        print('caps applied and data exported!')
        df[keep_cols + ['above_upper_cap','below_lower_cap'] + inc_draws].to_csv('{}/neo_eye_rb/{}.csv'.format(outdir, location_id))
    # otherwise, don't apply and copy incidence draws to output directory 
    else: 
        print('No caps being applied...')
        df = pd.read_csv('{}/neo_eye_rb/pre_winsorize/{}.csv'.format(utils.get_path(process='nonfatal_model',
                                                                                          key='incidence_temp_draws'),
                                                                           location_id))
        df[keep_cols + inc_draws].to_csv('{}/neo_eye_rb/{}.csv'.format(outdir, location_id))


if __name__ == "__main__":
    import sys 
    location = int(sys.argv[1])
    main(location)
