# Usage
IRIS is comprised of six main parts:

* Stage controller
* Spectrometer controller
* Mapping coordinate generator
* Raman imaging
* Brightfield imaging
* DataHub

## Stage and spectrometer controller
The stage and spectrometer controllers should hopefully be straightforward to use, with entry boxes to adjust parameters and buttons to directly control the instruments.

Note: The laser power parameter underneath the spectrometer controller section is not used in any calculations or operations; it is there simply to remind the user to take note of the laser parameters.

## Mapping operations (Raman and brightfield imaging)
Two mapping operations are possible: brightfield and Raman imaging, and both require the mapping coordinates to be generated to command the stages. To do so:

1. Navigate to the 'Coordinate generator' tab
2. Generate the coordinates (refer to the following 'Generating mapping coordinates' subsection)
3. Go to the Raman imaging or Brightfield imaging tab
4. Press the respective mapping buttons (i.e., the discrete or continuous mapping button for Raman imaging and the take image button for brightfield imaging)
5. Once pressed, the instruments will automatically move to perform the measurement
6. As the measurement is being performed, the data is saved to the DataHub in real time and can be seen in the 'Heatmap Plotter' section.

## Generating mapping coordinates
... coming soon ...

## Saving the data
To save the measurement data, simply head to the DataHub tab and click the save button. The app will notify the user once the saving process is completed.

**TLDR:** Use the database format to save space. These database files can also be loaded into the app again, but not the other tabular formats. Note: When moving the save file, make sure to move the entire folder, not just the .db file since all the spectra data are actually stored in the './data' subfolder.
There are two main formats to save the data:

1. In a tabular format (e.g., .csv, .txt, .parquet, etc.)
2. In a database format (.db)

.csv and .txt formats are simple and can be easily imported into other files, but they can take a lot more space than the other formats (currently supporting .parquet and .feather). For this reason, we have developed our own structure using an SQLite3 database format (the .db format) in conjunction with the parquet file format. This allows users to see into the data saved using an online database viewer, but also keeps the savefiles small in a separate './data' subfolder in parquet files. This saves more than 95% of the disk space used compared to .txt and .csv files. Additionally, these database files can also be loaded back into IRIS to review previous measurements. In short, we recommend using the **database format for long-term storage** and the **tabular format for importing into other software**.