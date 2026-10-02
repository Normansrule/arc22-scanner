# Glossary

Every term the build uses, in plain words. Acronyms are spelled out once here and in each document.

| Term | Meaning |
|---|---|
| **3MF** (3D Manufacturing Format) | a zipped 3D file that can hold several coloured parts; here optional and untested in Bambu Studio |
| **AMS** (Automatic Material System) | Bambu Lab's filament changer used for two-colour prints |
| **AWG** (American Wire Gauge) | wire size; 22 AWG is a sensible battery/5 V wire here |
| **Bare corner / bare zone** | a spot on a board you have *checked* has no parts or glass — the only place a printed support may touch |
| **Bounding box** | an object drawn around a detected thing on the photo |
| **B-rep** (boundary representation) | the exact solid CAD geometry before it is turned into triangles |
| **BOM** (Bill of Materials) | the parts list |
| **CAD** (Computer-Aided Design) | here: the Python/CadQuery model of the enclosure |
| **Closing swept volume** | all the space the right shell passes through while it is lowered onto the left half |
| **COCO** (Common Objects in Context) | a public dataset whose 80 everyday categories (person, cup, chair…) are the only things the detector can name |
| **Commissioning** | first power-up checks of display, touch and camera before enabling detection |
| **CS** (Chip Select) | the line that tells one SPI device "this message is for you" |
| **Dupont** | the common 2.54 mm jumper wire with crimped female/male housings |
| **Field / reserved field** | air the model keeps free for wires to exit, bend and relax, or for a plug to go in |
| **GPIO** (General-Purpose Input/Output) | a programmable pin of the ESP32; **3.3 V logic only** |
| **I2C** (Inter-Integrated Circuit) | a two-wire bus (SDA data, SCL clock); the camera uses it for sensor registers |
| **Inference** | running the trained neural network on a new image |
| **INT8** | 8-bit integer weights; a smaller, faster version of a model ("quantised") |
| **IP rating** (Ingress Protection) | a dust/water rating; ARC-22 has **none** |
| **JPEG** | the compressed photo format the camera sends |
| **Lay-in** | a board drops into its slots or clips from the open seam side, with no fasteners |
| **MISO / MOSI / SCLK** | SPI data from device, data to device, and clock |
| **NVS** (Non-Volatile Storage) | the ESP32's small flash key-value store (touch calibration, article cache) |
| **Object detection** | finding *where* things are in a photo and *what* they are |
| **PCB** (Printed Circuit Board) | the board itself |
| **PETG** (polyethylene terephthalate glycol) | the tough, slightly flexible filament used for both colours |
| **PSRAM** (Pseudo-Static RAM) | the ESP32-S3's extra 8 MB of memory (N16R8 = 16 MB flash, 8 MB PSRAM) |
| **SBOM** (Software Bill of Materials) | a machine-readable list of every software dependency and version |
| **SPI** (Serial Peripheral Interface) | a fast four-wire bus used by the display, touch and camera |
| **STEP** | editable, exact CAD exchange format |
| **STL** | triangle mesh for slicers; here four aligned colour regions |
| **Strain relief** | a little extra slack so a wire is never pulled straight out of its connector |
| **TLS** (Transport Layer Security) | the encryption under HTTPS |
| **Touch window** | the opening over the screen's active area |
| **VERIFY** | a value still taken from a reference drawing, not measured on your part |
| **YOLO** (You Only Look Once) | the family of fast object-detection networks; YOLO11n is its smallest member |
