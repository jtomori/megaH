megaH - megascans to Houdini integration
===========================

Setup
-----

##### 1. Add *houdini* folder from this repo into *HOUDINI_PATH* environment variable, for example add this line to your *houdini.env*
```
HOUDINI_PATH = "&;/home/myUser/megaH/houdini"
```

##### 2. Set *MEGA_LIB* environment variable pointing to the folder containing all megascans assets.
```
MEGA_LIB = "/home/myUser/megascans_library"
```


Usage
-----

- Sample library for testing can be found [here](https://goo.gl/Y2D9BA).
- After your environment variables are set up, in Houdini you can start using **Megascans tools** shelf.
  - **Crack OBJs** does required pre-process step which splits original OBJ asset sets into individual assets. This tool will recursively scan specified path for OBJs. It is required to run this step only once. If a new asset folder is added, then it is required to run this tool on the folder. Although this tool outputs assets in the OBJ geometry format, output file extension is *.objc* in order to easily distinguish it from original uncracked OBJ file.
  - **Index assets** scans through folders specified in *MEGA_LIB* path and looks for cracked OBJs, then it organizes it based into subassets and respective LODs and stores as a dictionary in a JSON file located in *MEGA_LIB/index.json*, it will overwrite *index.json* if it already exists
- As well there is a **Megascans** section in *TAB Menu* in *SOPs* containing related assets.
  - **Mega load** is assets loader, which provides simple UI for choosing desired asset.
    - *rename* option enables automatic renaming of the node to the name of a selected asset
    - *display* changes viewport preview complexity, does not effect rendered result
    - *textured* will show albedo texture in the viewport
    - *shaders*
      - *Find Shaders* button will automatically scan current Houdini project for the shaders associated with the megascans assets (specified in *MEGA_SHADER_\** environment variable)