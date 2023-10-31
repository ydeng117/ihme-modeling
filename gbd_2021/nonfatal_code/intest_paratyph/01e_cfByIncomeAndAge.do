* BOILERPLATE *
  clear all
  set maxvar 10000
  set more off
  
  if c(os)=="Unix" {
	local j = FILEPATH
	set odbcmgr unixodbc
	}
  else {
	local j = FILEPATH
	}

  
  
* DEFINE LOCALS *  
  local incModel  230849 //80171
  local typhModel 235913 //80901
  local paraModel 235916 //80903

  
  adopath + FILEPATH
*  run FILEPATH/get_draws.ado
  run FILEPATH/get_demographics.ado
  
  /*local team epi 
  get_demographics, gbd_team(`team') clear
  
  local ages `r(age_group_ids)'
  local ageList = subinstr("`ages'", " ", ",",.)
 */
  local measure 6

  tempfile locationTemp popTemp appendTemp mergeTemp


  
  
/******************************************************************************\		
    READ IN CHINA DATA TO ESTIMATE TYPHOID:PARATYPHOID CASE FATALITY RATIO  
\******************************************************************************/  

  foreach i in typhoid paratyphoid {
  
    import excel FILEPATH.XLSX, sheet("`i' fever") firstrow clear

    bysort year: egen cases  = total(reportincidence)
    bysort year: egen deaths = total(reportdeaths)
    bysort year: gen touse = _n ==_N
 
    generate typhoid = "`i'" == "typhoid"
   
    order year cases deaths typhoid

    keep if touse==1
    keep year cases deaths typhoid
  
    if "`i'" == "paratyphoid" append using `appendTemp'
  
    save `appendTemp', replace
	
    }


/******************************************************************************\		
              ESTIMATE TYPHOID:PARATYPHOID CASE FATALITY RATIO
\******************************************************************************/  
  
  glm deaths typhoid, family(binomial cases) eform
  
  local cfRatioB  = _b[typhoid]
  local cfRatioSe = _se[typhoid]
  
  
  
  
/******************************************************************************\		
                    BRING IN INCIDENCE & SPLIT ESTIMATES
\******************************************************************************/


* PULL INCIDENCE & POPULATION NUMBERS *
  use FILEPATH.dta, clear
  capture drop _m *Merge
  
  foreach var in age_group location year {
	levelsof `var'_id, local(`var's) clean
	}
	
  save `mergeTemp'
  
* PULL MODEL ESTIMATES *  
  foreach x in typh para {
	*get_estimates, gbd_team(`team') model_version_id(``x'Model') age_group_id(`ages') clear
	get_model_results, gbd_team("epi") model_version_id(``x'Model') age_group_id(`age_groups') year_id(`years') location_id(`locations') sex_id(1 2) clear

	keep location_id year_id age_group_id sex_id mean
	rename mean mean_`x'
	
	merge 1:1 location_id year_id age_group_id sex_id using `mergeTemp', assert(3) nogenerate
	save `mergeTemp', replace

	}


* CONVERT TOTAL INCIDENCE TO CAUSE-SPECIFIC NUMBERS *
  gen nTyph = incCases * mean_typh / (mean_typh + mean_para)
  gen nPara = incCases * mean_para / (mean_typh + mean_para)


* TOTAL UP CASE-SPECIFIC NUMBERS BY AGE AND INCOME *  
  fastcollapse nTyph nPara population, by(incomeCat age_group_id) type(sum)
  generate pTyph = nTyph / (nTyph + nPara)

  

  
/******************************************************************************\		
                     BRING IN CASE FATALITY MODEL RESULTS
\******************************************************************************/


merge 1:1 age_group_id incomeCat using FILEPATH.dta, assert(3) nogenerate   //FILEPATH.dta, assert(3) nogenerate
  
forvalues i = 0/999 {
  local ratio = exp(rnormal(`cfRatioB', `cfRatioSe'))
  quietly generate cf_para_`i'   = cf_`i'  / (`ratio' * pTyph + 1 - pTyph)
  quietly generate cf_typh_`i'   = cf_para_`i' * `ratio'
  di "." _continue
  }
  
drop cf_0-cf_999 population nTyph nPara pTyph
sort incomeCat age_group_id

egen cf_paraMean = rowmean(cf_para_*)
egen cf_typhMean = rowmean(cf_typh_*)
sort income age
br income age *Mean


save FILEPATH.dta, replace

forvalues i = 1/3 {
  preserve
  keep if incomeCat==`i'
  drop incomeCat
  save FILEPATH.dta, replace
  restore
  }
  


  
local j J:  
forvalues i = 1/3 {
  use FILEPATH.dta, clear
  
  expand 2 if inlist(age_group_id, 4, 5), gen(new)
  replace age_group_id = 388 if age_group_id==4 & new==0
  replace age_group_id = 389 if age_group_id==4 & new==1
  replace age_group_id = 238 if age_group_id==5 & new==0
  replace age_group_id = 34  if age_group_id==5 & new==1
  drop new

  saveold FILEPATH.dta, version(13) replace
  }
  
  