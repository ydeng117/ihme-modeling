// *********************************************************************************************************************************************************************
// *********************************************************************************************************************************************************************
// Author: 	NAME
// Date: 		04 August 2014
// Purpose:	Split edentulism parent into the tooth_loss state
// do "FILEPATH"

// PREP STATA
	clear
	set more off
	set maxvar 3200
	if c(os) == "Unix" {
		global prefix "ADDRESS"
		set odbcmgr unixodbc
		set mem 2g
	}
	else if c(os) == "Windows" {
		global prefix "ADDRESS"
		set mem 2g
	}

// Temp directory
	local tmp_dir "`1'"

// Reading parent model id num
	local edent_id `2'

// ME_id of results
	local child_id `3'

//  ME_id of asymptomatic results
	local asymp_id `4'

// location_id
	local loc `5'


// ****************************************************************************
// Log work
	capture log close
	log using "`tmp_dir'/`child_id'/00_logs/`loc'_draws.smcl", replace

// Load in necessary function
run "FILEPATH"

// Get symptomatic and asymptomatic prevalence and incidence
	foreach year in 1990 1995 2000 2005 2010 2015 2019 2020 2021 2022 {
	**foreach year in 2015 2019 {
		foreach sex in 1 2 {
			foreach metric in 5 6 {
				// Pull in draws of oral_edent
				get_draws, gbd_id_type("modelable_entity_id") gbd_id(`edent_id') measure_id(`metric') source("epi") location_id(`loc') year_id(`year') sex_id(`sex') age_group_id(2 3 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 30 31 32 34 235 238 388 389) status(best) gbd_round_id(7) decomp_step("iterative") clear
				gen metric = "prevalence_incidence"
				drop modelable_entity_id
				// merge on the tooth loss symptomatic proportion that was created in 00_master
				merge m:1 metric using "`tmp_dir'/`child_id'/tooth_loss_split.dta", assert(3) nogen
				// get symptomatic, by multiplying the draws by the symptomatic proportion
				forval y = 0/999 {
					gen symp_`y' = draw_`y'*prop_`y'
				}
				drop prop* metric
				// get asymptomatic, by subtracting the symptomatic from the total
				preserve
					forval y = 0/999 {
						replace draw_`y' = draw_`y' - symp_`y'
					}
					drop symp*
					outsheet using "`tmp_dir'/`asymp_id'/01_draws/`metric'_`loc'_`year'_`sex'.csv", comma names replace
				restore
				drop draw*
				renpfix symp draw
				outsheet using "`tmp_dir'/`child_id'/01_draws/`metric'_`loc'_`year'_`sex'.csv", comma names replace
			}
		}
	}


// *********************************************************************************************************************************************************************
// *********************************************************************************************************************************************************************
