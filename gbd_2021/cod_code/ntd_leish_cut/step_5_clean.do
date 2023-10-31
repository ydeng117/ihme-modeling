* Purpose: Creates master dataset of UHC values for each location
//
*** ======================= BOILERPLATE ======================= ***
	clear all
	set more off
	set maxvar 32767
	local code_root "FILEPATH"
	local data_root "FILEPATH"

	local exec_from_args : env EXEC_FROM_ARGS
	capture confirm variable exec_from_args, exact
	if "`exec_from_args'" == "True" {
		local params_dir 		`2'
		local draws_dir 		`4'
		local interms_dir		`6'
		local logs_dir 			`8'
	}
	else {
		local params_dir "FILEPATH/params"
		local draws_dir "FILEPATH/draws"
		local interms_dir "FILEPATH/interms"
		local logs_dir "FILEPATH/logs_dir"
	}

	cap log using "`logs_dir'/step_5_`location'.smcl", replace
	if !_rc local close_log 1
	else local close_log 0

	// Source relevant functions
	adopath + FILEPATH  // source STATA
    run FILEPATH/get_demographics.ado
    run FILEPATH/get_covariate_estimates.ado
  *************************
 

 *age metadata
    get_demographics,gbd_team("ADDRESS") gbd_round_id("ADDRESS")


	local years `r(year_ids)'
	local yearList `=subinstr("`r(year_ids)'", " ", ",", .)'
	local maxYear = 2022

***************************
import delimited "`params_dir'/ntd_leish_cut_lgr.csv", clear

keep if most_detailed==1

keep if year_start==2019

keep if value_endemicity==1

*generate variable to index location IDs

levelsof location_id, local(clCntryIds) clean

*pull file with one country output to access years - just to get the estimation frame 
use  "FILEPATH/incidence_draws/ADDRESS.dta", clear
*store years in macro variable
levelsof year_id, local(years) clean
*define temporary files for storing covariate information
tempfile hsa 

*pull in UHC values for all locations
	
	get_covariate_estimates, covariate_id(1097) year_id(`years') decomp_step("iterative") gbd_round_id("ADDRESS") location_id(`clCntryIds') clear
	
	
	keep if inrange(year_id, 1989, 2018)

    keep location_id year_id mean_value
    
   
	save "FILEPATH/uhc.dta",replace
	