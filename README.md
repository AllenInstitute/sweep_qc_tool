sweep qc tool
=============

A GUI application for performing manual quality control on in vitro ephys experiments.

installation
------------

We provide binary packages for Windows, which you can download from [the releases page](https://github.com/AllenInstitute/sweep_qc_tool/releases). To install on Windows:
1. download `sweep_qc_tool.zip`
2. unzip the archive and move the resulting directory to your desired install location
3. run `sweep_qc_tool.exe` to start the tool

To run on OSX or Linux you should:
1. clone this repository to your desired install location using `git clone https://github.com/alleninstitute/sweep_qc_tool`
2. create an environment using e.g. conda or virtualenv. For instance, if using virtualenv on Linux, you might run:
    ```
    cd sweep_qc_tool
    python3 -m venv .venv
    ```
    to create your virtual environment. You would then activate this environment using `source .venv/bin/activate`.
3. With your environment activated, install the dependencies by running
    ```
    pip install -r requirements/base.txt
    ```
4. You can now start the tool either via `fbs run` or via `python src/main/python/main.py`.)

If you invoke the sweep qc tool from the command line, you can customize its behavior by passing optional arguments. See [the main file](src/main/python/main.py) for documentation of these parameters.

usage
-----

#### QCing sweeps

With the tool running, you will most likely want to load some data! Navigate to `File->load data set from NWB file` and select the NWB file containing your data in the resulting dialog. You ought to see something like:
![sweep table](doc/resources/sweep_view_basic_fx_outdated.jpg)

You can get started right away QCing sweeps. Whenever you see an auto QC state that looks wrong, adjust the manual QC state from `default` to `passed` or `failed` using the dropdown menu. If you want a closer look at one of the images, simply click the thumbnail for an zoomable and pannable popup plot:
![looking at the peak of the test epoch response](doc/resources/zoom_on_peak.jpg)
When you are done, select `File->Export manual states to JSON` to save your work.

#### Viewing extracted features

In the bottom right corner of the sweep page (the first image above) you should see a red message warning that `cell features are outdated`. Indeed, if you switch over to the `Features` tab, you will see a blank page! To calculate cell-level features, use `Edit->Run feature extraction`. Now when you select the `Features` tab, you ought to see something like this (after a short wait):
![cell features](doc/resources/cell_features.jpg)
When you run feature extraction, cell-level features are calculated using the set of passed sweeps. Each time you change this set by failing or passing a sweep, the cell features become outdated, and the warning message will return.


level of support
----------------
We are actively using and maintaing this code. We welcome issues (particularly bug reports) and pull requests from the community, but cannot promise to address them on any fixed schedule.

How to make your own sweep filters
----------------------------------
1. In `sweep_table_view.py`, add a `QAction` to `SweepTableView.__init__()`

2. In the `init_actions()` method of `SweepTableView`, 
set the menu action as checkable with `.setCheckable(True)`, 
connect the action with `.toggled.connect(self.filter_sweeps)`, 
and set the action as disabled initially with `.setEnabled(False)`

5. In the `.filter_sweeps()` method of `SweepTableView`, add appropriate checkbox logic

6. In `main.py`, set the initial status of the checkbox in `SweepPage.set_default_filter_states()`
with `.setEnabled(True)` and `.setChecked(True)` or `.setChecked(False)`

7. Also in `main.py`, add the action to the menu in `MainWindow.add_menu_actions()`