# HEAD

# Version 1.5.1 [#13](https://github.com/Frastandreetto/StripThesis/pull/13)
The WN level and the knee frequency of the FFT of the Scientific Data are stored in a txt file.

# Version 1.5.0
New features and fixes in the Pipeline [#12](https://github.com/Frastandreetto/StripThesis/pull/12):
- Adding new flag `noise_level`: if it is enabled, the code will calculate the WN level and the 1/f of the FFT of the Scientific Data.

# Version 1.4.0
New features and fixes in the Pipeline [#11](https://github.com/Frastandreetto/StripThesis/pull/11)
- Fix Data Normalization into a datetime conversion;
- Add downsampling features to correlation plots;
- Add two new HK parameters: POL_MODE and PIN_CON;
- Fix data visualization in Csv Reports. Fixing reports names;
- Fix holes in outputs: time jumps topic;
- Fix plots style
- Add elapsed time to the pipeline workflow

# Version 1.3.3
Fixing Userguide for the new version [#10](https://github.com/Frastandreetto/StripThesis/pull/10)


# Version 1.3.2
Fixing dependences in op_runner.py and official_pipeline.py to run the pipeline on the EGSE @ INAF-OAS Cryowaves Laboratory.
Adding Userguide for the version [#9](https://github.com/Frastandreetto/StripThesis/pull/9)

# Version 1.3.1
Adding Userguide for the version [#8](https://github.com/Frastandreetto/StripThesis/pull/8) - Fixing comments.

# Version 1.3.0
Adding a new feature to the class ThermalSensors in thermalsensors.py [#5](https://github.com/Frastandreetto/StripThesis/pull/5):
- Plot_FFT_TS -> all_in parameter to plot all FFT in one plot

# Version 1.2.0
Adding a new method to the class Polarimeter in polarimeter.py [#4](https://github.com/Frastandreetto/StripThesis/pull/4):
- Plot_Band, with some little updates [#7](https://github.com/Frastandreetto/StripThesis/pull/7)

# Version 1.1.0
Adding some new tools in f_strip.py [#6](https://github.com/Frastandreetto/StripThesis/pull/6):
- Adding Statistics to data_plot: mean, dev std, max, min
- Adding Bin Function
- Adding Tags functions: get tags from hdf5 filename, get tags from start_time and end_time in iso str, get start_time & end_time from tag.

# Version 1.0.0
-   **Breaking change**: new CLI which provides help and supports the commands `tot` `pol_hk` and `thermal_hk` to provide three different analysis: a global one, the polarimeter housekeeping one and the thermal sensors one. The official_pipeline can be used both from the command line and through some handy TOML files. [#3](https://github.com/Frastandreetto/StripThesis/pull/3)

# Version 0.2.0
 
-   Fix many issues on the functions. Pipeline presented on March 29th for my Master Defence [#2](https://github.com/Frastandreetto/StripThesis/pull/2)

# Version 0.1.0

-   First release of the code. Some easy functions for a first analysis during my Master Thesis [#1](https://github.com/Frastandreetto/StripThesis/pull/1)
