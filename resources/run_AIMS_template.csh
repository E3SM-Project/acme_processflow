#!/bin/csh

#
# Template driver script to generate coupled diagnostics on rhea
#
#Basic usage:
#       1. Activate the environment, set:
#               a. export NCL_PATH= /usr/local/src/NCL-6.3.0/bin
#               b. export CONDA_PATH=/export/evans99/miniconda2/bin:$NCL_PATH:$PATH
#               c. source activate /export/evans99/miniconda2
#       2. copy this template to something like run_AIMS_$user.csh
#       3. open run_AIMS_$user.csh and set user defined, case-specific variables
#       4. execute: csh run_AIMS_$user.csh

#Meaning of acronyms/words used in variable names below:
#       test:           Test case
#       ref:            Reference case
#       ts:             Time series; e.g. test_begin_yr_ts, here ts refers to time series
#       climo:          Climatology
#       begin_yr:       Model year to start analysis
#       end_yr:         Model year to end analysis
#       condense:       Create a new file for each variable with time series data for that variable.
#                       This is used to create climatology (if not pre-computed) and in generating time series plots
#       archive_dir:    Location of model generated output directory
#       scratch_dir:    Location of directory where the user wants to store files generated by the diagnostics.
#                       This includes climos, remapped climos, condensed files and data files used for plotting.
#       short_term_archive:     Adds /atm/hist after the casename. If the data sits in a different structure, add it after
#       the casename in test_casename
setenv PATH                             %%nco_path%%:$PATH

set projdir =                           %%coupled_project_dir%%
set coupled_diags_home =                %%coupled_diags_home%%
#USER DEFINED CASE SPECIFIC VARIABLES TO SPECIFY (REQUIRED)

#Test case variables, for casename, add any addendums like /run or /atm/hist
setenv test_casename                    %%test_casename%%
setenv test_native_res                  %%test_native_res%%
setenv test_archive_dir                 %%test_archive_dir%%
setenv test_short_term_archive          0
setenv test_begin_yr_climo              %%test_begin_yr_climo%%
setenv test_end_yr_climo                %%test_end_yr_climo%%
setenv test_begin_yr_ts                 %%test_begin_yr_ts%%
setenv test_end_yr_ts                   %%test_end_yr_ts%%

#Atmosphere switches (True(1)/False(0)) to condense variables, compute climos, remap climos and condensed time series file
#If no pre-processing is done (climatology, remapping), all the switches below should be 1
setenv test_compute_climo               1
setenv test_remap_climo                 1
setenv test_condense_field_climo        1       #ignored if test_compute_climo = 0
                                                #if test_condense_field_climo = 1 and test_compute_climo = 0
                                                #the script will look for a condensed file
setenv test_condense_field_ts           1
setenv test_remap_ts                    1

#Reference case variables (similar to test_case variables)
setenv ref_case                         %%ref_case%%
setenv ref_archive_dir                  %%ref_archive_dir%%

#ACMEv0 ref_case info for ocn/ice diags
# IMPORTANT: the ACMEv0 model data MUST have been pre-processed. If this pre-processed data is not available, set ref_case_v0 to None.
setenv ref_case_v0                      None
setenv ref_archive_v0_ocndir            None
setenv ref_archive_v0_seaicedir         None

#The following are ignored if ref_case is obs
setenv ref_native_res                   None
setenv ref_short_term_archive           None
setenv ref_begin_yr_climo               None
setenv ref_end_yr_climo                 None
setenv ref_begin_yr_ts                  None
setenv ref_end_yr_ts                    None

setenv ref_condense_field_climo         1
setenv ref_condense_field_ts            1
setenv ref_compute_climo                1
setenv ref_remap_climo                  1
setenv ref_remap_ts                     1

#Set yr_offset for ocn/ice time series plots
#setenv yr_offset 1999    # for 2000 time slices
setenv yr_offset                        %%yr_offset%%    # for 1850 time slices

#Set ocn/ice specific paths to mapping files locations
# IMPORTANT: user will need to change mpas_meshfile and mpas_remapfile *if* MPAS grid varies.
#     EXAMPLES of MPAS meshfiles:
#      $projdir/milena/MPAS-grids/ocn/gridfile.oEC60to30.nc  for the EC60to30 grid
#      $projdir/milena/MPAS-grids/ocn/gridfile.oRRS30to10.nc for the RRS30to10 grid
#     EXAMPLES of MPAS remap files:
#      $projdir/mapping/maps/map_oEC60to30_TO_0.5x0.5degree_blin.160412.nc  remap from EC60to30 to regular 0.5degx0.5deg grid
#      $projdir/mapping/maps/map_oRRS30to10_TO_0.5x0.5degree_blin.160412.nc remap from RRS30to10 to regular 0.5degx0.5deg grid
#      $projdir/mapping/maps/map_oRRS15to5_TO_0.5x0.5degree_blin.160412.nc  remap from RRS15to5 to regular 0.5degx0.5deg grid
#
#     Finally, note that pop_remapfile is not currently used
setenv mpas_meshfile                    %%mpas_meshfile%%
setenv mpas_remapfile                   %%mpas_remapfile%%
setenv pop_remapfile                    %%pop_remapfile%%

#Select sets of diagnostics to generate (False = 0, True = 1)
setenv generate_atm_diags               1
setenv generate_ocnice_diags            1

#The following ocn/ice diagnostic switches are ignored if generate_ocnice_diags is set to 0
setenv generate_ohc_trends              1
setenv generate_sst_trends              1
setenv generate_sst_climo               1
setenv generate_seaice_trends           1
setenv generate_seaice_climo            1

#Other diagnostics not working currently, work in progress
setenv generate_moc                     0
setenv generate_mht                     0
setenv generate_nino34                  0

#Generate standalone html file to view plots on a browser, if required
setenv generate_html                    1
###############################################################################################


#OTHER VARIABLES (NOT REQUIRED TO BE CHANGED BY THE USER - DEFAULTS SHOULD WORK, USER PREFERENCE BASED CHANGES)

#Set paths to scratch, logs and plots directories
setenv test_scratch_dir                 $projdir/$USER/$test_casename.test.pp
setenv ref_scratch_dir                  $projdir/$USER/$ref_case.test.pp
setenv plots_dir                        $projdir/$USER/coupled_diagnostics_${test_casename}-$ref_case
setenv log_dir                          $projdir/$USER/coupled_diagnostics_${test_casename}-$ref_case.logs

#Set atm specific paths to mapping and data files locations
setenv remap_files_dir                  %%remap_files_dir%%
setenv GPCP_regrid_wgt_file             %%GPCP_regrid_wgt_file%%
setenv CERES_EBAF_regrid_wgt_file       %%CERES_EBAF_regrid_wgt_file%%
setenv ERS_regrid_wgt_file              %%ERS_regrid_wgt_file%%

#Set ocn/ice specific paths to data file names and locations
setenv mpas_climodir                    $test_scratch_dir

setenv obs_ocndir                       %%obs_ocndir%%
setenv obs_seaicedir                    %obs_seaicedir%%
setenv obs_sstdir                       %%obs_sstdir%%
setenv obs_iceareaNH                    %%obs_iceareaNH%%
setenv obs_iceareaSH                    %%obs_iceareaSH%%
setenv obs_icevolNH                     %%obs_icevolNH%%
setenv obs_icevolSH                     None

#Location of website directory to host the webpage
setenv www_dir /var/www/acme/acme-diags/$USER

##############################################################################
###USER SHOULD NOT NEED TO CHANGE ANYTHING HERE ONWARDS######################

#setenv coupled_diags_home $PWD

#LOAD THE ANACONDA-2.7-CLIMATE ENV WHICH LOADS ALL REQUIRED PYTHON MODULES
# put this in your .bash_profile:
# NCL_PATH = /usr/local/src/NCL-6.3.0/bin
# NCO_PATH = /export/zender1/bin
#CONDA_PATH = /export/evans99/miniconda2 (installed by user, see confluence for documentation)

# then type "source activate uvcdat-nightly "

#PUT THE PROVIDED CASE INFORMATION IN CSH ARRAYS TO FACILITATE READING BY OTHER SCRIPTS
csh_scripts/setup.csh

#RUN DIAGNOSTICS
if ($generate_atm_diags == 1) then
        $coupled_diags_home/ACME_atm_diags.csh
endif

if ($generate_ocnice_diags == 1) then
        $coupled_diags_home/ACME_ocnice_diags.csh
endif

#GENERATE HTML PAGE IF ASKED
source $log_dir/case_info.temp

set n_cases = $#case_set

@ n_test_cases = $n_cases - 1

foreach j (`seq 1 $n_test_cases`)

        if ($generate_html == 1) then
                csh csh_scripts/generate_html_index_file.csh    $j \
                                                                $plots_dir \
                                                                $www_dir
        endif
end
