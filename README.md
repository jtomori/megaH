megaH - megascans to Houdini integration
===========================

Installation
------------

##### 1. Add *houdini* folder from this repo into *HOUDINI_PATH* environment variable, for example add this line to your *houdini.env*
```
HOUDINI_PATH = &;/home/myUser/megaH/houdini
```

##### 2. Set *MEGA_LIB* environment variable pointing to the folder containing all megascans assets.
```
MEGA_LIB = /home/myUser/megascans_library
```


Usage
-----

- Sample library for testing can be found [here](https://goo.gl/Y2D9BA).
- After your environment variables are set up, in Houdini you can start using *Megascans tools* shelf.
  - *Crack OBJs* does required pre-process step which splits original OBJ asset sets into individual assets. This tool will recursively scan specified path for OBJs. It is required to run this step only once. If a new asset folder is added, then it is required to run this tool on the folder. Although this tool outputs assets in the OBJ geometry format, output file extension is *.objc* in order to easily distinguish it from original uncracked OBJ file.
  - *Index assets* scans through folders specified in *MEGA_LIB* path and looks for cracked OBJs (with .objc file extension), then it organizes it based into subassets and respective LODs and stores as a dictionary in a JSON file located in *MEGA_LIB/index.json*, it will overwrite *index.json* if it already exists