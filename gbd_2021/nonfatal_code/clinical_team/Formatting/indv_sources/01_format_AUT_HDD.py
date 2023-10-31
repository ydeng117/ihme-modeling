# -*- coding: utf-8 -*-
"""
Created on Mon Jan 23 17:32:28 2017
@author:

Format the raw data for Austria. This replaces the script at:

PLEASE put link to GHDx entry for the source here
"""
import pandas as pd
import platform
import numpy as np
import sys
import warnings
import time
import glob
import os
import getpass

user = getpass.getuser()
# load our functions
prep_path = r"FILEPATH"
sys.path.append(prep_path)

import hosp_prep

# Environment:
if platform.system() == "Linux":
    root = "FILEPATH"
else:
    warnings.warn("You must run this on the cluster")
    exit
    # root = "FILEPATH"

# switch to write dta files to HDF in /raw or read in the existing HDFs
write_hdf_helper = False
if write_hdf_helper:
    start = time.time()
    #####################################################
    # READ DATA AND KEEP RELEVANT COLUMNS
    # ASSIGN FEATURE NAMES TO OUR STRUCTURE
    #####################################################
    # AUT data isn't stored in a uniform manner so hardcode paths
    drivelesspaths = [
        "FILEPATH",
        "FILEPATH",
        "FILEPATH",
        "FILEPATH",
        "FILEPATH",
        "FILEPATH",
    ]

    # read data into a list then concat it together
    df_list = []
    for f in drivelesspaths:
        print("Reading in file {}".format(f))
        adf = pd.read_stata(root + f)

        to_drop = adf.filter(regex="^(MEL)").columns
        adf.drop(to_drop, axis=1, inplace=True)

        # rename all the 2ndary dx cols
        if "AD1" in adf.columns:
            for i in np.arange(1, 44, 1):
                dxnum = str(i + 1)
                adf.rename(columns={"AD" + str(i): "dx_" + dxnum}, inplace=True)
        if "NEBEN1" in adf.columns:
            for i in np.arange(1, 13, 1):
                dxnum = str(i + 1)
                adf.rename(columns={"NEBEN" + str(i): "dx_" + dxnum}, inplace=True)
        adf.to_hdf(
            "FILEPATH",
            key="df",
            format="table",
            complib="blosc",
            complevel=6,
            mode="w",
        )
        print((time.time() - start) / 60)
else:
    start = time.time()
    globby = root + r"FILEPATH"

    # this is for the production run
    df_list = [pd.read_hdf(f, "df") for f in glob.glob(globby)]
    print((time.time() - start) / 60)

# The datasets with 40+ nonprimary dx are too large to process together
# split them up by input file and process
final_list = []  # append all the processed dfs to this list
for df in df_list:

    assert df.shape[0] == len(df.index.unique()), (
        "index is not unique, "
        + "the index has a length of "
        + str(len(df.index.unique()))
        + " while the DataFrame has "
        + str(df.shape[0])
        + " rows"
        + "try this: df = df.reset_index(drop=True)"
    )

    # Drop these cols when present
    cols = df.columns
    drops = ["bundeslpat", "verlurs", "NEBEN_ANZAHL", "anzlst", "anzvlst", "aufnzl"]
    to_drop = [c for c in cols if c in drops]
    df.drop(to_drop, axis=1, inplace=True)

    # Replace feature names on the left with those found in data where appropriate
    # ALL OF THESE COLUMNS WILL BE MADE unless you comment out the ones you don't
    # want
    hosp_wide_feat = {
        "nid": "nid",
        "location_id": "location_id",
        "representative_id": "representative_id",
        # 'year': 'year',
        "berj": "year_start",
        "year_end": "year_end",
        "geschlnum": "sex_id",
        "alterentle": "age",
        "age_group_unit": "age_group_unit",
        "code_system_id": "code_system_id",
        # measure_id variables
        "entlartnum": "outcome_id",
        "facility_id": "facility_id",
        # diagnosis varibles
        "viersteller": "dx_1",
    }

    # Rename features using dictionary created above
    df.rename(columns=hosp_wide_feat, inplace=True)

    # set difference of the columns you have and the columns you want,
    # yielding the columns you don't have yet
    new_col_df = pd.DataFrame(
        columns=list(set(hosp_wide_feat.values()) - set(df.columns))
    )
    df = df.join(new_col_df)

    #####################################################
    # FILL COLUMNS THAT SHOULD BE HARD CODED
    # this is where you fill in the blanks with the easy
    # stuff, like what version of ICD is in the data.
    #####################################################

    # These are completely dependent on data source

    # -1: "Not Set",
    # 0: "Unknown",
    # 1: "Nationally representative only",
    # 2: "Representative for subnational location only",
    # 3: "Not representative",
    # 4: "Nationally and subnationally representative",
    # 5: "Nationally and urban/rural representative",
    # 6: "Nationally, subnationally and urban/rural representative",
    # 7: "Representative for subnational location and below",
    # 8: "Representative for subnational location and urban/rural",
    # 9: "Representative for subnational location, urban/rural and below",
    # 10: "Representative of urban areas only",
    # 11: "Representative of rural areas only"

    df["representative_id"] = 1  # Do not take this as gospel, it's guesswork
    df["location_id"] = 75

    # group_unit 1 signifies age data is in years
    df["age_group_unit"] = 1
    df["source"] = "AUT_HDD"

    # code 1 for ICD-9, code 2 for ICD-10
    df["code_system_id"] = 2  # icd 10 after 2000
    df.loc[df.year_start <= 2000, "code_system_id"] = 1

    df["facility_id"] = "inpatient unknown"
    df["year_end"] = df["year_start"]

    # convert outcome ID to str
    df["outcome_id"] = df["outcome_id"].astype(str)
    # convert sex_id to str
    df["sex_id"] = df["sex_id"].astype(str)

    missing_out = df[df.outcome_id == "nan"].shape[0]
    print(
        (
            "There are {} null values in the outcome ID column. This should be"
            r" looked into. Setting to discharge for now".format(missing_out)
        )
    )
    if missing_out > 0:
        df.loc[df.outcome_id == "nan", "outcome_id"] = "discharge"
        # df.outcome_id.fillna('discharge', inplace=True)

    # case is the sum of live discharges and deaths
    # df['outcome_id'] = "case/discharge/death"
    pre_outcomes = df.outcome_id.notnull().sum()
    df["outcome_id"] = df["outcome_id"].replace(
        ["discharged alive", "Discharged (alive)", "dead", "Dead"],
        ["discharge", "discharge", "death", "death"],
    )
    assert (
        pre_outcomes == df.outcome_id.notnull().sum()
    ), "Some null outcomes were introduced"
    assert set(df.outcome_id) == set(
        ["discharge", "death"]
    ), "There are outcomes that aren't death or discharge"

    missing_sex = df[df.sex_id == "nan"].shape[0]
    print(
        (
            "There are {} null values in the sex_id column. Setting to 3".format(
                missing_sex
            )
        )
    )
    if missing_sex > 0:
        # df.sex_id.fillna(3, inplace=True)
        df.loc[df.sex_id == "nan", "sex_id"] = 3

    pre_sexes = df.sex_id.notnull().sum()
    df["sex_id"] = df["sex_id"].replace(
        ["Male", "male", "Female", "female"], [1, 1, 2, 2]
    )
    assert pre_sexes == df.sex_id.notnull().sum()
    for s in df.sex_id.unique():
        assert s in [1, 2, 3], "data includes an unusable sex id"

    print(
        (
            "There are {} null values and {} blank values in the dx_1 column."
            r" Setting to 'cc_code'".format(
                df.dx_1.isnull().sum(), df[df.dx_1 == ""].shape[0]
            )
        )
    )
    df.loc[df.dx_1.isnull(), "dx_1"] = "cc_code"
    df.loc[df.dx_1 == "", "dx_1"] = "cc_code"

    # metric_id == 1 signifies that the 'val' column consists of counts
    df["metric_id"] = 1

    # Create a dictionary with year-nid as key-value pairs
    nid_dictionary = {
        1989: 121917,
        1990: 121841,
        1991: 121842,
        1992: 121843,
        1993: 121844,
        1994: 121845,
        1995: 121846,
        1996: 121847,
        1997: 121848,
        1998: 121849,
        1999: 121850,
        2000: 121851,
        2001: 121831,
        2002: 121854,
        2003: 121855,
        2004: 121856,
        2005: 121857,
        2006: 121858,
        2007: 121859,
        2008: 121860,
        2009: 121862,
        2010: 121863,
        2011: 121832,
        2012: 128781,
        2013: 205019,
        2014: 239353,
    }
    df = hosp_prep.fill_nid(df, nid_dictionary)

    #####################################################
    # CLEAN VARIABLES
    #####################################################

    # Columns contain only 1 optimized data type
    int_cols = [
        "location_id",
        "year_start",
        "year_end",
        "age_group_unit",
        "age",
        "sex_id",
        "nid",
        "representative_id",
        "metric_id",
    ]
    # BE CAREFUL WITH NULL VALUES IN THE STRING COLUMNS, they will be converted
    # to the string "nan"
    # fast way to cast to str while preserving Nan:
    # df['casted_foo'] = df.foo.loc[df.foo.notnull()].map(str)
    str_cols = ["source", "facility_id", "outcome_id"]

    # use this to infer data types
    # df.apply(lambda x: pd.lib.infer_dtype(x.values))

    if df[str_cols].isnull().any().any():
        warnings.warn(
            "\n\n There are NaNs in the column(s) {}".format(
                df[str_cols].columns[df[str_cols].isnull().any()]
            )
            + "\n These NaNs will be converted to the string 'nan' \n"
        )

    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="raise", downcast="integer")
    for col in str_cols:
        df[col] = df[col].astype(str)

    # Turn 'age' into 'age_start' and 'age_end'
    #   - bin into year age ranges
    #   - under 1, 1-4, 5-9, 10-14 ...

    df.loc[df["age"] > 95, "age"] = 95  # this way everything older than GBD
    # terminal age start will be lumped into the terminal age group.

    # drop null ages
    pre = df.shape[0]
    df = df[df.age.notnull()]
    assert (
        df.shape[0] - pre <= 220
    ), "We expected 220 null ages but more than this were lost"
    pre = df.shape[0]
    df = hosp_prep.age_binning(df)
    if df.shape[0] < pre:
        print(df)
        assert False, "Age binning has caused rows to be dropped"
    df.drop("age", axis=1, inplace=True)  # changed age_binning to not drop age col

    # AUT marks infants as 1 year olds
    df.loc[df["age_start"] == 1, "age_start"] = 0

    # mark unknown sex_id
    df.loc[(df["sex_id"] != 1) & (df["sex_id"] != 2), "sex_id"] = 3

    #####################################################
    # SWAP E AND N CODES
    # AUT does not appear to contain external cause of injury codes
    #####################################################

    # =============================================================================
    # get list of dx cols
    diagnosis_feats = df.columns[df.columns.str.startswith("dx_")]

    # clean cols after reshaping long b/c it's much faster
    # Remove non-alphanumeric characters from dx feats
    for feat in diagnosis_feats:
        df[feat] = hosp_prep.sanitize_diagnoses(df[feat])

    # store the data wide for the EN matrix
    # data is being processed by year groups so take the min year_start value and use
    # that to name the file
    min_year = df.year_start.unique().min()
    df_wide = df.copy()
    df_wide["metric_discharges"] = 1
    df_wide = (
        df_wide.groupby(df_wide.columns.drop("metric_discharges").tolist())
        .agg({"metric_discharges": "sum"})
        .reset_index()
    )
    df_wide.to_stata(
        r"FILEPATH", write_index=False,
    )
    # save the data wide
    wide_path = "FILEPATH"
    hosp_prep.write_hosp_file(df_wide, wide_path, backup=True)
    del df_wide
    #####################################################
    # IF MULTIPLE DX EXIST:
    # TRANSFORM FROM WIDE TO LONG
    #####################################################

    if len(diagnosis_feats) > 1:
        print("Reshaping long")

        # check primary dx
        pre_dx1_counts = df.dx_1.value_counts()
        # check secondary dx (I can't figure out why the indices are diff)
        pre_otherdx_counts = (
            df[diagnosis_feats.drop("dx_1")]
            .apply(pd.Series.value_counts)
            .sum(axis=1)
            .reset_index()
            .sort_values("index")
            .reset_index(drop=True)
        )

        # break tests on purpose
        # s = df[df.dx_7.notnull()].sample(1)
        # df = pd.concat([df, s])

        # create index of everything that's not a dx column
        indx = df.columns.drop(df.filter(regex="^(dx)").columns)
        # df = df.melt(id_vars=indx)  # this doesn't work in python 2??
        df = pd.melt(df, id_vars=list(indx), value_vars=list(diagnosis_feats))
        # drop nulls and blanks
        df = df[df["value"].notnull()]

        post_dx1_counts = df[df.variable == "dx_1"].value.value_counts()
        post_otherdx_counts = (
            df[df.variable != "dx_1"]
            .value.value_counts()
            .reset_index()
            .sort_values("index")
            .reset_index(drop=True)
        )

        assert (
            pre_dx1_counts == post_dx1_counts
        ).all(), "Reshaping long has altered the primary diagnoses"
        # compare non primary icd codes
        assert (
            pre_otherdx_counts["index"] == post_otherdx_counts["index"]
        ).all(), "Reshaping long has altered the nonprimary diagnoses"
        # compare non primary value counts
        assert (
            pre_otherdx_counts[0] == post_otherdx_counts["value"]
        ).all(), "Reshaping long has altered the nonprimary diagnoses"
        # rename to cause code
        df.rename(
            columns={"variable": "diagnosis_id", "value": "cause_code"}, inplace=True
        )
        # convert from many level dx to just 2
        pre_dx1 = df[df.diagnosis_id == "dx_1"].shape[0]  # count of dx 1 rows
        pre_other = df.shape[0] - pre_dx1  # count of dx2+ rows for testing
        df.diagnosis_id = np.where(df.diagnosis_id == "dx_1", 1, 2)
        assert (
            pre_dx1 == df[df.diagnosis_id == 1].shape[0]
        ), "Counts of primary diagnosis levels do not match"
        assert (
            pre_other == df[df.diagnosis_id == 2].shape[0]
        ), "Counts of nonprimary diagnosis levels do not match"

        print("Done reshaping long in {}".format((time.time() - start) / 60))

    elif len(diagnosis_feats) == 1:
        df.rename(columns={"dx_1": "cause_code"}, inplace=True)
        df["diagnosis_id"] = 1

    else:
        print("Something went wrong, there are no ICD code features")

    # drop the rows which were blank in the original data, this shouldn't affect
    # primary dx
    pre = df[df.diagnosis_id == 1].shape[0]
    df = df[df.cause_code != ""]
    assert pre == df[df.diagnosis_id == 1].shape[0]
    # If individual record: add one case for every diagnosis
    df["val"] = 1

    #####################################################
    # GROUPBY AND AGGREGATE
    #####################################################

    # Check for missing values
    print("Are there missing values in any row?\n")
    null_condition = df.isnull().values.any()
    if null_condition:
        warnings.warn(">> Yes.  ROWS WITH ANY NULL VALUES WILL BE LOST ENTIRELY")
    else:
        print(">> No.")

    # Group by all features we want to keep and sums 'val'
    group_vars = [
        "cause_code",
        "diagnosis_id",
        "sex_id",
        "age_start",
        "age_end",
        "year_start",
        "year_end",
        "location_id",
        "nid",
        "age_group_unit",
        "source",
        "facility_id",
        "code_system_id",
        "outcome_id",
        "representative_id",
        "metric_id",
    ]
    df = df.groupby(group_vars).agg({"val": "sum"}).reset_index()

    #####################################################
    # ARRANGE COLUMNS AND PERFORM INTEGRITY CHECKS
    #####################################################

    # Arrange columns in our standardized feature order
    columns_before = df.columns
    hosp_frmat_feat = [
        "age_group_unit",
        "age_start",
        "age_end",
        "year_start",
        "year_end",
        "location_id",
        "representative_id",
        "sex_id",
        "diagnosis_id",
        "metric_id",
        "outcome_id",
        "val",
        "source",
        "nid",
        "facility_id",
        "code_system_id",
        "cause_code",
    ]
    df = df[hosp_frmat_feat]
    columns_after = df.columns

    # check if all columns are there
    assert set(columns_before) == set(
        columns_after
    ), "You lost or added a column when reordering"
    for i in range(len(hosp_frmat_feat)):
        assert (
            hosp_frmat_feat[i] in df.columns
        ), "%s is missing from the columns of the DataFrame" % (hosp_frmat_feat[i])

    # check data types
    for i in df.columns.drop(["cause_code", "source", "facility_id", "outcome_id"]):
        # assert that everything but cause_code, source, measure_id (for now)
        # are NOT object
        assert df[i].dtype != object, "%s should not be of type object" % (i)

    # verify column data
    onetwo = set([1, 2])
    assert (
        df.nid.unique().size == df.year_start.unique().size
    ), "There should be a unique nid for each year"
    assert set(df.diagnosis_id.unique()).issubset(
        onetwo
    ), "There are undefined diagnosis id levels"
    assert set(df.sex_id.unique()).issubset(
        set([1, 2, 3])
    ), "There are undefined sex ids present"
    assert set(df.code_system_id.unique()).issubset(
        onetwo
    ), "There are undefined code system ids present"

    # check number of unique feature levels
    assert len(df["year_start"].unique()) == len(
        df["nid"].unique()
    ), "number of feature levels of years and nid should match number"
    assert len(df["age_start"].unique()) == len(df["age_end"].unique()), (
        "number of feature levels age start should match number of feature "
        + r"levels age end"
    )
    assert (
        len(df["diagnosis_id"].unique()) <= 2
    ), "diagnosis_id should have 2 or less feature levels"
    assert (
        len(df["sex_id"].unique()) <= 3
    ), "There should at most three feature levels to sex_id"
    assert (
        len(df["code_system_id"].unique()) <= 2
    ), "code_system_id should have 2 or less feature levels"
    if len(df["source"].unique()) != 1:
        print(
            (
                "source should only have one feature level {} {}".format(
                    df.source.unique(), df.source.value_counts(dropna=False)
                )
            )
        )
        assert False  # break the script

    assert (df.val >= 0).all(), "for some reason there are negative case counts"
    final_list.append(df)

final_df = pd.concat(final_list, ignore_index=True)

# somehow 50 blank diagnoses crept back in
final_df = final_df[final_df.cause_code != ""]
#####################################################
# WRITE TO FILE
#####################################################

# Saving the file
write_path = root + r"FILEPATH"
hosp_prep.write_hosp_file(final_df, write_path, backup=True)
