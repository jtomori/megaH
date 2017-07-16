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

##### 3. Set *MEGA_SHADER* environment variable to the operator name of a shader (OTL Operator Type, which can be seen by right-clicking on the shader asset and selecting *Type Properties...*) you want to use for your assets. (this variable is optional, it is used for automatic shader assignment)
```
MEGA_SHADER = "jt_megaShader"
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
    - *shader*
      - *Find Shader* button will automatically scan current Houdini project for the shader associated with the megascans assets (specified in *MEGA_SHADER* environment variable)
        - this asset is setting up *packed disk primitive* to the correct path on the disk and it also sets various attributes required for the shading pointing to the textures included in Megascans library
          - those string attributes include: *disp, norm, albedo, rough, spec, lod* for displacement, normal map, diffuse albedo, specular roughness, specular intensity/tint and lod information, which can be used in shader logic (it will contain one of the following values: *High, 0, 1, 2, 3, 4, 5*)
          - note that in case of *High* LOD selected, normal map will use *NormalBump* texture.