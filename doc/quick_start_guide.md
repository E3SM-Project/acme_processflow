# Super Quick Start Guide

Use this guide if you're already an acme1 or aims4 user.

### Anaconda

If your user doesnt have anaconda installed, you will need to install anaconda for environment and package management. You can check if you have conda by simply running ```conda``` If the command fails, your user doesnt have conda in your path. If it works, skip the anaconda installation step.

* Simply run the installer from the cached copy on the server

    ```bash /p/cscratch/acme/bin/Anaconda2-4.3.1-Linux-x86_64.sh```

* The installer will ask you some questions, unless you want to customize it in some way, just type 'yes' and hit enter for all of them.


* Start a new bash shell with the new environment variables.
    ```bash```

For a new run you'll need to create an input directory and setup your runs configuration file. Make a copy of the sample config file.
```
mkdir /p/cscratch/acme/USER_NAME/PROJECT/input
cd /p/cscratch/acme/USER_NAME/PROJECT/input
wget https://raw.githubusercontent.com/sterlingbaldwin/acme_workflow/master/run.cfg
```

## Setup Run Config
Once you have the file, open run.cfg in your favorite editor. There are are 9 values that must be changed before you're ready to run. You can find an explanation of each of them [here](setup_guide.md), or [below](#config)

The keys you need to change before running the first time are:
```
[global]
    # The directory to hold post processing output
    output_path = /p/cscratch/acme/USER_NAME/PROJECT/output

    # The directory to store model output
    data_cache_path = /p/cscratch/acme/USER_NAME/PROJECT/input

    # The path on the remote machine to look for model output
    source_path = /scratch2/scratchdirs/golaz/ACME_simulations/20170313.beta1_02.A_WCYCL1850S.ne30_oECv3_ICG.edison/run

    # The year to start the post processing, typically 1
    simulation_start_year =  1

    # The last year to run post processing jobs on
    simulation_end_year = 20

    # The list of year lengths to run jobs on
    set_frequency = 5, 10

    # The experiment name
    experiment = case_scripts

    # The batch system type to submit to, currently only slurm is supported (PBS in the future)
    batch_system_type = slurm

    # The base URL for the server thats hosting image output
    img_host_server = https://acme-viewer.llnl.gov

    # The email address to send to when all processing is complete, leave commented out to turn off
    email = your_email@llnl.gov

    # The regular expressions to use to search for files on the remote machine
    [[patterns]]
        STREAMS = "streams"
        ATM = "cam.h0"
        MPAS_AM = "mpaso.hist.am.timeSeriesStatsMonthly"
        MPAS_CICE = "mpascice.hist.am.timeSeriesStatsMonthly"
        MPAS_RST = "mpaso.rst.0"
        MPAS_O_IN = "mpas-o_in"
        MPAS_CICE_IN = "mpas-cice_in"
        RPT = "rpointer"
        # Add custom file types here for example
        # ATM_HIST_1 = "cam.h1"
        # ATM_HIST_2 = "cam.h2"

    # The jobs to run on each set, to turn off the job entirely leave its value blank
    [[set_jobs]]
        # this will run ncclimo for both 5 and 10
        ncclimo = 5, 10
        # this will run time series only at 10
        timeseries = 10
        # this will run amwg only at 5
        amwg = 5
        # this will turn off the coupled diag 
        coupled_diag = 

```

* For each run, the contents of output_path will be overwritten.

#### Atmospheric only runs

This configuration setup assumes you want to run all the diagnostics, including the coupled_diags. If you're interested in an atmosphere only run, there are two changes to make. First, there's no need to transfer all the files, only the ATM files. Second, coupled_diag should be turned off

Change these:
```
[global]
...
    [[patterns]]
        STREAMS = "streams"
        ATM = "cam.h0"
        MPAS_AM = "mpaso.hist.am.timeSeriesStatsMonthly"
        MPAS_CICE = "mpascice.hist.am.timeSeriesStatsMonthly"
        MPAS_RST = "mpaso.rst.0"
        MPAS_O_IN = "mpas-o_in"
        MPAS_CICE_IN = "mpas-cice_in"
        RPT = "rpointer"
        # Add custom file types here
        # ATM_HIST_1 = "cam.h1"
        # ATM_HIST_2 = "cam.h2"

    [[set_jobs]]
        ncclimo = 5, 10
        timeseries = 5, 10
        amwg = 5, 10
        coupled_diag = 5, 10
```

To these:

```
[global]
...
    [[patterns]]
        ATM = "cam.h0"
       
...
    [[set_jobs]]
        ncclimo = 5, 10
        timeseries = 5, 10
        amwg = 5, 10
        coupled_diag = 
```

### Config Explanation<a name="config"></a>

#### output_path
This is the local path to store processed output

#### data_cache_path
This is the local path to store unprocessed model data

#### simulation_end_year
The highest year number to expect

#### set_frequency
A list of lengths of processing sets. E.g set_frequency = [5, 10] will run the processing jobs for every 5 years, and every 10 years. If run on 10 years of data, it will create 3 job sets, 1-5, 6-10, 1-10

#### source_path
The path on the source_endpoint to look for model output.

#### source_endpoint
A globus endpoind UUID, the default is edison.nersc.gov. You can find globus endpoints by [going here](https://www.globus.org/app/endpoints) and using the globus search features.

#### destination_endpoint
The globus endpoint UUID for the machine doing the post-processing. The default is acme1.llnl.gov.

#### email
The email address you would like notified when the run completes.

## Running

Running on acme1 and aims4 is very easy. Simply activate the conda environment provided, and run the script. 

The run.cfg can exist where ever you like, use the -c flag followed by the path to the config. Once you start the run, you will need to authenticate with Globus for the file transfers. You can find a walk through of the [globus authentication process here](globus_authentication_walkthrough.md)

While running in UI mode, all stderr is redirected to a file in your output directory named workflow.error.

```
source activate /p/cscratch/acme/bin/acme
python /p/cscratch/acme/bin/acme_workflow/workflow.py -c run.cfg
```

In interactive mode, if the terminal is closed or you log out, it will stop the process (but the runs managed by SLURM will continue). See below for headless mode instructions.

    python /p/cscratch/acme/bin/acme_workflow/workflow.py -c run.cfg

![initial run](images/initial_run.png)

Once globus has transfered the first year_set of data, it will start running the post processing jobs.

![run in progress](images/run_in_progress.png)


#### headless mode
A run in headless mode wont stop if you close the terminal. The run will continue until it finishes, at which point it will send an email to you with the results. If there is an error, you can stop the run with the command ```kill <PID>``` where PID is the process id.
```
nohup python /p/cscratch/acme/bin/acme_workflow/workflow.py -c run.cfg --no-ui &
```

This run can continue after you close the termincal and log off the computer. While running in headless mode, you can check run_state.txt for the run status. This file can be found in your output directory.

```
cd /p/cscratch/acme/<YOUR_USER_NAME>/output
less run_state.txt
```

![run_state](images/run_state.png)