# Purpose: 1) Set hyperparameters for space-time
#
# Notes: 1) DDM's run_all will execute this script passing version_id and saving in "inputs" folder on "FILEPATH"


rm(list=ls())
library(data.table)
library(readr)
library(argparse)
library(mortdb)
library(mortcore)

parser <- ArgumentParser()
parser$add_argument('--version_id', type="integer", required=TRUE,
                    help='The version id for this run of DDM')
args <- parser$parse_args()

version_id <- args$version_id

out_dir <- paste0("FILEPATH")

hyper_param <- data.table(iso3_sex_source = character(), graph_id = character(),lambda = double())

# Default
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "default", graph_id = "default",lambda = 1))

# TUR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "TUR_both_VR", graph_id = "TUR&&both&&VR", lambda = 0.5))

# MNG
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MNG_both_VR", graph_id = "MNG&&both&&VR",lambda = 0.5))

# BRN
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "BRN_both_VR", graph_id = "BRN&&both&&VR",lambda = 0.5))

# JOR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "JOR_both_VR", graph_id = "JOR&&both&&VR",lambda = 0.5))

# LBY
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "LBY_both_VR", graph_id = "LBY&&both&&VR",lambda = 0.5))

# FJI
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "FJI_both_VR", graph_id = "FJI&&both&&VR",lambda = 0.5))

# GUAM
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "GUM_both_VR", graph_id = "GUM&&both&&VR",lambda = 0.5))

# BGD Household
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "BGD_both_HOUSEHOLD", graph_id = "BGD&&both&&HOUSEHOLD",lambda = 0.5))

# IND SRS
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "IND_both_SRS", graph_id = "IND&&both&&SRS",lambda = 0.5))

# ZAF Household
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "ZAF_both_HOUSEHOLD", graph_id = "ZAF&&both&&HOUSEHOLD",lambda = 0.5))

# ZAF VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "ZAF_both_VR", graph_id = "ZAF&&both&&VR",lambda = 0.5))

# BFA Census
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "BFA_both_CENSUS", graph_id = "BFA&&both&&CENSUS",lambda = 0.5))

# ECU VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "ECU_both_VR", graph_id = "ECU&&both&&VR",lambda = 0.5))

# HND VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "HND_both_VR", graph_id = "HND&&both&&VR",lambda = 0.3))

# HTI VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "HTI_both_VR", graph_id = "HTI&&both&&VR",lambda = 0.5))

# KOR VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "KOR_both_VR", graph_id = "KOR&&both&&VR",lambda = 0.5))

# MAR VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MAR_both_VR", graph_id = "MAR&&both&&VR",lambda = 0.5))

# MAR VR - male
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MAR_male_VR", graph_id = "MAR&&male&&VR",lambda = 0.5))

# MAR VR - female
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MAR_female_VR", graph_id = "MAR&&female&&VR",lambda = 0.5))

# MHL VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MHL_both_VR", graph_id = "MHL&&both&&VR",lambda = 0.5))

# MLI Census
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MLI_both_CENSUS", graph_id = "MLI&&both&&CENSUS",lambda = 0.5))

# MWI CENSUS
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MWI_both_CENSUS", graph_id = "MWI&&both&&CENSUS",lambda = 0.5))

# MWI Household
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "MWI_both_HOUSEHOLD", graph_id = "MWI&&both&&HOUSEHOLD",lambda = 0.5))

# NPL Census
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "NPL_both_CENSUS", graph_id = "NPL&&both&&CENSUS",lambda = 0.5))

# PAK SRS
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "PAK_both_SRS", graph_id = "PAK&&both&&SRS",lambda = 0.5))

# PNG VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "PNG_both_VR", graph_id = "PNG&&both&&VR",lambda = 0.5))

# SAU Census
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "SAU_both_CENSUS", graph_id = "SAU&&both&&CENSUS",lambda = 0.5))

# SAU Survey
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "SAU_both_SURVEY", graph_id = "SAU&&both&&SURVEY",lambda = 0.5))

# SAU VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "SAU_both_VR", graph_id = "SAU&&both&&VR",lambda = 0.5))

# SAU VR - male
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "SAU_male_VR", graph_id = "SAU&&male&&VR",lambda = 0.5))

# SAU VR - female
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "SAU_female_VR", graph_id = "SAU&&female&&VR",lambda = 0.5))

# STP Census
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "STP_both_CENSUS", graph_id = "STP&&both&&CENSUS",lambda = 0.5))

# TON VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "TON_both_VR", graph_id = "TON&&both&&VR",lambda = 0.5))

# TUN VR
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "TUN_both_VR", graph_id = "TUN&&both&&VR",lambda = 0.5))

# CHN_44533 DSP
hyper_param <- rbind(hyper_param, data.table(iso3_sex_source = "CHN_44533_both_DSP", graph_id = "CHN_44533&&both&&DSP",lambda = 0.5))

write_csv(hyper_param, paste0("FILEPATH"))

# DONE
