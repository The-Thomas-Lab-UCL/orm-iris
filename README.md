# ORM-IRIS
Open Raman Microscopy - Integrated Raman Imaging Software (ORM-IRIS or IRIS) is a complementary controller software of the modular [Open Raman Microscopy (ORM) system](www.openramanmicroscopy.org). IRIS is a **GUI-based app** to easily control a motorised Raman microscope (XY-stage, Z-stage, brightfield camera, and a spectrometer) for Raman imaging, offering full instrument controls, automatic Raman imaging, brightfield imaging and tiling, data management, basic data analyses, and more. It supports instruments from various manufacturers and is designed to be **completely modular**, including Ocean Optics, Andor, Princeton Instruments, Thorlabs, Physik Instrumente, Zaber, and more, such that controllers can be easily swapped within seconds by simply changing the chosen instruments in the config file.

## GUI example
<img width="452" height="239" alt="image" src="https://github.com/user-attachments/assets/a31565e7-f03e-4eca-aaa8-e7f5365b04cd" />

## Usage
IRIS is comprised of six main parts:
- Stage controller
- Spectrometer controller
- Mapping coordinate generator
- Raman imaging
- Brightfield imaging
- DataHub

### Stage and spectrometer controller
The stage and spectrometer controllers should hopefully be straightforward to use, with entry boxes to adjust parameters and buttons to directly control the instruments.

Note: The laser power parameter underneath the spectrometer controller section is not used in any calculations or operations; it is there simply to remind the user to take note of the laser parameters.

### Mapping operations (Raman and brightfield imaging)
Two mapping operations are possible: brightfield and Raman imaging, and both require the mapping coordinates to be generated to command the stages. To do so:
1. Navigate to the 'Coordinate generator' tab
2. Generate the coordinates (refer to the following 'Generating mapping coordinates' subsection)
3. Go to the Raman imaging or Brightfield imaging tab
4. Press the respective mapping buttons (i.e., the discrete or continuous mapping button for Raman imaging and the take image button for brightfield imaging)
5. Once pressed, the instruments will automatically move to perform the measurement
6. As the measurement is being performed, the data is saved to the DataHub in real time and can be seen in the 'Heatmap Plotter' section.

### Generating mapping coordinates
... documentation to be completed ...

### Saving the data
To save the measurement data, simply head to the DataHub tab and click the save button. The app will notify the user once the saving process is completed.

**TLDR:** Use the database format to save space. These database files can also be loaded into the app again, but not the other tabular formats. Note: When moving the save file, make sure to move the entire folder, not just the .db file since all the spectra data are actually stored in the './data' subfolder.
There are two main formats to save the data:
1. In a tabular format (e.g., .csv, .txt, .parquet, etc.)
2. In a database format (.db)

.csv and .txt formats are simple and can be easily imported into other files, but they can take a lot more space than the other formats (currently supporting .parquet and .feather). For this reason, we have developed our own structure using an SQLite3 database format (the .db format) in conjunction with the parquet file format. This allows users to see into the data saved using an online database viewer, but also keeps the savefiles small in a separate './data' subfolder in parquet files. This saves more than 95% of the disk space used compared to .txt and .csv files. Additionally, these database files can also be loaded back into IRIS to review previous measurements. In short, we recommend using the **database format for long-term storage** and the **tabular format for importing into other software**.

## Installation
At the moment, we are still in the middle of creating a detailed installation instruction. In the meantime, please contact us at kevin.uning.23@ucl.ac.uk. We would be happy to have a video call to assist with your installations.
But if you would like to attempt this on your own:
1. Install Python (preferably 3.12.x or 3.13.x)
   - Make sure to check the 'Documentation', 'pip', 'tcl/tk and IDLE', and 'py launcher' during the installation under the 'Optional Features' window (see the screenshot below).
   - If this step is missed, finish installing Python, and restart the computer, and rerun the installation file. This should allow you to modify the previous installation and to enable these features.
3. Install the 'GitHub Desktop' app (this makes it easy to track changes and to keep using the same version)
4. Install your preferred code editor (e.g., Visual Studio Code)
5. Restart the computer (this prevents any potential unfinished installation issues)
6. Open GitHub Desktop and clone this repository into your local hard disk
7. Open the cloned repository folder in your code editor
8. Open the terminal in the code editor (PowerShell)
9. Install the orm-iris package by running 'py -m pip install .' in the terminal
10. Open and run main_controller.py
    - This should open the GUI (similar to the screenshot above).
    - And should create a config.ini and config_shortcuts.ini files in the root directory.
    - If you could see the GUI, congratulations! You have successfully installed the 
11. Turn off the app and follow the instructions in the next section to configure the config.ini file according to your microscope instruments.

Optionally, a virtual environment can be set up before running step 7 (but this can cause a lot of confusion during the installation process, so unless familiar with the process, feel free to leave this out).

https://www.alphr.com/wp-content/uploads/2022/08/install-5.png<img width="660" height="402" alt="image" src="https://github.com/user-attachments/assets/7479ecd4-bb4d-455c-931a-19439ca35901" />
(Screenshot obtained from: https://www.alphr.com/install-pip-windows/ on the 22nd October 2025)

## Configuring the instruments
Instrument configurations can be easily done in the config.ini file generated during the first run. To do so:
1. Install the necessary packages related to the instrument. Please refer to the following 'Instrument controller package installation' subsection before proceeding.
2. Open the config.ini file using your text editor (notepad) or your code editor.
3. Navigate to the 'CONTROLLER CHOICES' section and modify the controllers accordingly
   - At the moment, it should all be 'dummy'. Simply replace it with your instrument (the options are provided in the same line, after the ';' symbol. Be careful not to remove the ';' symbol). e.g., replace 'dummy' with 'thorlabs_mono' for a Thorlabs monochrome camera.
4. Save the config.ini file
5.  Run the IRIS app to check if the instrument is running properly (by running the 'main_controller.py' file to open the GUI)
6. Repeat step 1 to 5 for each instrument.

Note: All the instruments can technically be installed simultaneously, but installing them one at a time is much easier to troubleshoot if a problem occurs.

## Instrument controller package installation
Please follow these step-by-step instructions to install your instrument controllers, and do not hesitate to contact us if any problem occurs.
Typical issues:
- If the instrument is being connected to another app (e.g., the native controller app) they often would not work with the ORM-IRIS. This is due to the device's communication lock/limitation as they are only designed to communicate with one software at a time.
- When entering directory or file **paths** in the config.ini file, it has to be enclosed with an ' or a ", e.g., C:\path\to\file will return an error. Instead, it has to be 'C:\path\to\file' or "C:\path\to\file".
- When entering a value in the config.ini file, each value has to be ended with a comma ',' symbol, and the comments have to be preceeded by a semicolon ';' symbol.
- After modifying the config.ini file, it has to be saved before rerunning the app.

### Webcam
If your computer's native camera app can open the camera, it should also work with the app without any further modifications.

### Thorlabs Scientific cameras
1. Locate the Python SDK of your camera. It should be named 'thorlabs_tsi_camera_python_sdk_package.zip'
2. Copy the file's full path (e.g., 'C:\path\to\folder\thorlabs_tsi_camera_python_sdk_package.zip')
3. Open the PowerShell
4. Install the package by typing in 'py -m pip install 'C:\path\to\folder\thorlabs_tsi_camera_python_sdk_package.zip'
   - Note: if using a virtual environment, make sure to activate the environment before this step.

### Thorlabs Kinesis stages (M30XY/M, Z825B, PFM450, etc.)
For Thorlabs Kinesis stages, simply install the Kinesis software without changing the installation path. Then, add the serial number of your instrument (as shown in the Thorlabs Kinesis software) into the config.ini file in the 'CONTROLLER SPECIFIC PARAMETERS' section.

### Physik Instrumente stages
1. Open PowerShell (and activate the virtual environment if used)
2. Install the package by typing in 'py -m pip install PIPython'

### Zaber stages
1. Open PowerShell (and activate the virtual environment if used)
2. Install the package by typing in 'py -m pip install zaber_motion'
3. Open the Zaber native controller software and take note of the commport
4. Insert the commport value into the config.ini file under the 'zaber_comport' parameter

### Ocean Optics spectrometers (QEPro line)
1. Find the spectrometer's SDK folder (it should contain an 'OceanDirect.dll' file)
2. Copy the directory (folder)'s path
3. Insert the path into the config.ini file under the 'oceaninsight_api_dirpath' parameter

### Andor spectrometers
1. Download and install the Andor Driver Pack (Andor Driver Pack - 2.104.30167.0 (CCD,ICCD & EMCCD) from https://andor.oxinst.com/downloads/view/andor-driver-pack-2.104.30167.0-(ccd,iccd-emccd))
2. Find and copy the atmcd64d.dll and the atspectrograph.dll file paths (e.g., 'C:\path\to\folder\atspectrograph.dll'
3. Insert the paths into the 'andor_atmcd64d_dll_path' and 'andor_atspectrograph_dll_path' parameters

### Princeton Instruments spectrometers
1. Install the PICam in the folder 'C:\Program Files\Princeton Instruments\PICam' (which should be the default folder)
