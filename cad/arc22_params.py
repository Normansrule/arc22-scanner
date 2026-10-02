"""
ARC-22 FitFirst — every fit dimension in one place.

Coordinate system (ASSEMBLY coordinates, used by STEP/BREP and all checks):
  X = front-back   (0 = rear face, +X toward the front bow / camera)
  Y = width        (seam plane Y = 0; LEFT shell is Y <= 0, RIGHT shell is Y >= 0)
  Z = height       (0 = bottom of the grip bar)
Units: millimetres.

Rules
-----
* Every value that depends on YOUR physical parts is listed in MEASURED and
  starts life flagged VERIFY. Measure your unit (docs/MEASUREMENTS.md), put the
  numbers in measurements/my_units.toml, and rebuild. The build prints every
  value that is still unverified.
* Never "fix" a fit by scaling the scanner. Change a named value, relocate a
  part, or reshape a non-critical region.
"""
from __future__ import annotations

import copy
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent
MEAS_FILE = ROOT.parent / "measurements" / "my_units.toml"

# ---------------------------------------------------------------------------
# MEASURED values: (value, source). source "VERIFY" = nominal/reference guess.
# ---------------------------------------------------------------------------
MEASURED: dict[str, tuple[float, str]] = {
    # --- Display: Hosyond 4.0" ST7796S + XPT2046 (MSP4021 reference) -------
    "DISP_PCB_W": (61.74, "VERIFY: MSP4021 reference drawing (short side, becomes Y)"),
    "DISP_PCB_H": (108.04, "VERIFY: MSP4021 reference drawing (long side, becomes Z)"),
    "DISP_PCB_T": (1.6, "VERIFY: calipers on bare PCB edge"),
    "DISP_ACTIVE_W": (55.68, "VERIFY: MSP4021 reference active area"),
    "DISP_ACTIVE_H": (83.52, "VERIFY: MSP4021 reference active area"),
    "DISP_ACTIVE_OFF_Z": (4.0, "VERIFY: active-area centre minus PCB centre, +Z = away from header"),
    "DISP_ACTIVE_OFF_Y": (0.0, "VERIFY"),
    "DISP_GLASS_W": (61.0, "VERIFY: outer glass/touch-film width"),
    "DISP_GLASS_H": (97.0, "VERIFY: outer glass/touch-film height"),
    "DISP_GLASS_OFF_Z": (2.5, "VERIFY: glass centre minus PCB centre, +Z = away from header"),
    "DISP_GLASS_STACK": (4.6, "VERIFY: PCB front face to glass front face"),
    "DISP_BACK_POP": (4.0, "VERIFY: tallest part on PCB back (SD slot etc.), excluding header"),
    "DISP_HDR_SPACER": (2.5, "VERIFY: header plastic spacer height on PCB back"),
    "DISP_HDR_PINS": (14, "VERIFY: pin count of the display header"),
    "DISP_HDR_INSET": (3.0, "VERIFY: header row centre distance from its PCB edge"),
    "DISP_BARE_SIDE": (5.0, "VERIFY: bare strip width inward from each long PCB edge at the corners"),
    "DISP_BARE_END_HDR": (6.0, "VERIFY: bare PCB length at the header end (front face, beyond glass)"),
    "DISP_BARE_END_FAR": (2.5, "VERIFY: bare PCB length at the far end (front face, beyond glass)"),
    # --- Camera: Arducam Mini / Mini Plus OV2640 2MP SPI ------------------
    "CAM_PCB_W": (24.4, "VERIFY: ARC22 assumption (Y)"),
    "CAM_PCB_H": (34.1, "VERIFY: ARC22 assumption (Z)"),
    "CAM_PCB_T": (1.6, "VERIFY"),
    "CAM_HOLDER_SQ": (14.5, "VERIFY: S-mount (M12) holder base square"),
    "CAM_LENS_D": (14.0, "VERIFY: lens barrel outer diameter at the front"),
    "CAM_LENS_PROJ": (20.0, "VERIFY: PCB front face to lens front"),
    "CAM_OPT_OFF_Z": (3.0, "VERIFY: optical centre minus PCB centre, +Z = away from header"),
    "CAM_OPT_OFF_Y": (0.0, "VERIFY"),
    "CAM_BACK_POP": (3.0, "VERIFY: tallest part on camera PCB back"),
    "CAM_HDR_INSET": (2.0, "VERIFY: header row centre distance from bottom PCB edge"),
    "CAM_BARE_CORNER": (4.0, "VERIFY: bare square at each PCB corner (no parts, both faces)"),
    "CAM_HDR_PINS": (8, "Arducam Mini interface: CS MOSI MISO SCLK GND VCC SDA SCL"),
    # --- ESP32-S3-N16R8 dev board (DevKitC-1 style clone) ------------------
    "ESP_L": (69.0, "VERIFY: board length (becomes X)"),
    "ESP_W": (25.5, "VERIFY: board width (becomes Z)"),
    "ESP_T": (1.6, "VERIFY"),
    "ESP_TOP_POP": (3.4, "VERIFY: tallest part on top (module shield / USB-C)"),
    "ESP_HDR_LEN": (55.88, "VERIFY: 22 pins x 2.54"),
    "ESP_HDR_SPACER": (2.5, "VERIFY"),
    "ESP_USB_PROJ": (1.5, "VERIFY: USB-C shell overhang beyond PCB end"),
    "ESP_BARE_CORNER": (3.0, "VERIFY: bare corner square (component side) at all four corners"),
    "ESP_HDR_OFF_X": (0.0, "VERIFY: header-row centre minus board centre along the board length"),
    "ESP_USB_HALF_SPAN": (11.0, "VERIFY: half-span across the USB-C connector(s) at the USB end"),
    "USB_PLUG_T": (7.0, "VERIFY: thickness of YOUR programming cable's USB-C overmold"),
    "USB_PLUG_W": (12.4, "VERIFY: width of YOUR programming cable's USB-C overmold"),
    # --- Dupont / wiring ----------------------------------------------------
    "DUPONT_HOUSING_L": (14.0, "VERIFY: female housing length measured on YOUR jumpers"),
    "DUPONT_HOUSING_W": (2.6, "VERIFY"),
    "WIRE_STRAIGHT_EXIT": (6.0, "VERIFY: straight wire after the housing before bending"),
    "WIRE_BEND_R": (10.0, "VERIFY: first RELAXED bend radius of your jumper bundle"),
    "WIRE_STRAIN": (3.0, "strain-relief allowance"),
    # --- Power parts --------------------------------------------------------
    "BAT_L": (69.0, "VERIFY: Adafruit #354 reference (becomes Z)"),
    "BAT_W": (37.0, "VERIFY: (becomes X)"),
    "BAT_T": (18.0, "VERIFY: (becomes Y)"),
    "CHG_L": (21.0, "VERIFY: Adafruit #6106 length along the USB-C axis (X)"),
    "CHG_W": (26.0, "VERIFY: width (Y)"),
    "CHG_H": (11.0, "VERIFY: PCB + tallest part (terminal block)"),
    "CHG_BARE_CORNER": (3.0, "VERIFY: bare square at the two front PCB corners (both faces)"),
    "CHG_USB_OFF_Y": (-6.0, "VERIFY: USB-C centre minus board centre along Y"),
    "BTN_HOLE_D": (12.5, "VERIFY: panel cut-out for the 12 mm latching button"),
    "BTN_BODY_D": (15.0, "VERIFY: largest body/nut diameter behind the panel"),
    "BTN_DEPTH": (22.0, "VERIFY: panel inner face to end of terminals + solder"),
    # --- Hardware -----------------------------------------------------------
    "M2_HEAD_D": (3.8, "VERIFY: screw head diameter (<= ~4)"),
    "FOAM_T": (0.8, "choose 0.5-1.0 mm non-conductive foam"),
}

# ---------------------------------------------------------------------------
# DESIGN values (choices, not measurements)
# ---------------------------------------------------------------------------
DESIGN: dict[str, float] = {
    # body envelope — ARC22 bounds ~218 x 218 x 118
    "BODY_X": 218.0,
    "BODY_Z": 218.0,
    "BODY_Y": 118.0,
    "WALL": 2.8,
    "REAR_CORNER_R": 32.0,  # D-profile rear corners (must exceed SIDE_FILLET_R)
    "SIDE_FILLET_R": 28.0,  # rounded shoulders on both faces
    "BOW_START_X": 150.0,  # top/bottom are straight to here, then the elliptical bow
    # grip bar under the hand loop (rounded, much narrower than the head)
    "GRIP_HALF_W": 19.0,
    "GRIP_R": 12.0,
    "GRIP_OVERLAP": 12.0,  # how far the bar runs into each leg
    # hand loop (through-hole along Y)
    "LOOP_X0": 50.0,
    "LOOP_X1": 148.0,
    "LOOP_Z0": 30.0,
    "LOOP_Z1": 78.0,
    "LOOP_CORNER_R": 20.0,
    "LOOP_EDGE_R": 4.0,
    # camera fairing (integrated upper-bow nose)
    "CAM_AXIS_Z": 172.0,
    "FAIR_R": 24.0,
    "FAIR_X0": 150.0,
    "FAIR_FRONT_X": 206.0,
    "FAIR_FRONT_FILLET": 8.0,
    "LENS_RADIAL_GAP": 1.0,
    "LENS_RECESS": 1.0,  # lens front sits this far behind the fairing face
    # display placement (portrait on the rear face)
    "DISP_Z0": 80.0,  # bottom edge of display PCB (header edge)
    "DISP_GLASS_GAP": 0.8,  # air gap between wall and glass (nothing touches glass)
    "WINDOW_MARGIN": 1.0,
    "WINDOW_CHAMFER": 1.6,
    # ESP32 placement (standing in LEFT shell, component side facing the wall)
    "ESP_CX": 95.0,
    "ESP_CZ": 140.0,
    "ESP_WALL_GAP": 2.2,  # component tops to wall; also lets the USB-C plug overmold clear the wall
    "PROG_CORRIDOR_L": 35.0,  # USB plug + first bend when programming (case open)
    # battery (front leg, straddles seam)
    "BAT_X0": 152.0,
    "BAT_Z0": 42.0,
    # charger (rear leg, PCB horizontal, USB-C out of the rear face)
    "CHG_X0": 3.4,  # PCB rear edge; receptacle mouth flush with the wall inner face
    "CHG_Z0": 46.0,  # PCB bottom face
    "CHG_CY": -5.0,  # board centre Y  (USB-C lands at CHG_CY + CHG_USB_OFF_Y)
    "USB_SLOT_W": 10.5,
    "USB_SLOT_H": 4.6,
    "USB_OVERMOLD_W": 13.4,
    "USB_OVERMOLD_H": 7.6,
    "USB_OVERMOLD_DEPTH": 2.2,  # leaves WALL - 2.2 = 0.6 mm at the port so the plug fully mates
    # button (rear face, LEFT shell)
    "BTN_Z": 67.0,
    "BTN_Y": -13.0,
    # retention
    "SLOT_EXTRA": 0.2,  # extra free play in slots on top of foam
    "EDGE_GAP": 0.3,  # PCB edge to side stop
    "JAW_T": 2.4,
    "CLIP_T": 1.4,
    "CLIP_HOOK": 0.8,
    # screws (M2, self-tapping into PETG; no inserts)
    "M2_CLEAR_D": 2.4,
    "M2_PILOT_D": 1.7,
    "M2_WELL_D": 4.6,
    "BOSS_D": 8.0,
    "SCREW_SEAT_TO_SEAM": 5.0,  # right-shell material under the head
    "SCREW_ENGAGE_TARGET": 6.0,
    # seam lip / groove
    "LIP_H": 1.6,
    "LIP_T": 1.2,
    "LIP_CLEAR": 0.2,
    # cable routes
    "ROUTE_R": 5.0,
    # printer
    "BED": 256.0,
    "BED_MARGIN": 10.0,
}

# Screw positions (X, Z). Chosen to stay clear of every module keep-out.
SCREWS: list[tuple[str, float, float]] = [
    ("S1_rear_top", 16.0, 203.0),
    ("S2_top_mid", 100.0, 202.0),
    ("S3_bow", 196.0, 126.0),
    ("S4_front_low", 172.0, 29.0),
    ("S5_rear_low", 17.0, 18.0),
    ("S6_grip", 100.0, 14.0),
]


class P:
    """Attribute access to every parameter; tracks unverified measurements."""

    def __init__(self) -> None:
        self._measured = copy.deepcopy(MEASURED)
        self._design = dict(DESIGN)
        self.unverified: list[str] = []
        self._load_overrides()
        for k, (v, src) in self._measured.items():
            setattr(self, k, float(v))
            if src.upper().startswith("VERIFY"):
                self.unverified.append(k)
        for k, v in self._design.items():
            setattr(self, k, float(v))
        self.screws = list(SCREWS)
        self._derive()

    def _load_overrides(self) -> None:
        if not MEAS_FILE.exists():
            return
        data = tomllib.loads(MEAS_FILE.read_text())
        for k, v in data.get("measured", {}).items():
            if k not in self._measured:
                raise KeyError(f"{MEAS_FILE.name}: unknown measurement {k}")
            self._measured[k] = (float(v), "MEASURED (my_units.toml)")
        for k, v in data.get("design", {}).items():
            if k not in self._design:
                raise KeyError(f"{MEAS_FILE.name}: unknown design value {k}")
            self._design[k] = float(v)

    def _derive(self) -> None:
        # plug envelope depth behind a male header measured from the PCB face
        self.PLUG_DEPTH = self.DUPONT_HOUSING_L + self.DISP_HDR_SPACER
        self.WIRE_FIELD = (self.PLUG_DEPTH + self.WIRE_STRAIGHT_EXIT
                           + self.WIRE_BEND_R + self.WIRE_STRAIN)
        self.SLOT_GAP_ADD = 2 * self.FOAM_T + self.SLOT_EXTRA
        # display stack along +X from the rear wall
        self.DISP_GLASS_FRONT_X = self.WALL + self.DISP_GLASS_GAP
        self.DISP_PCB_FRONT_X = self.DISP_GLASS_FRONT_X + self.DISP_GLASS_STACK
        self.DISP_PCB_BACK_X = self.DISP_PCB_FRONT_X + self.DISP_PCB_T
        self.DISP_Z1 = self.DISP_Z0 + self.DISP_PCB_H
        self.DISP_CZ = self.DISP_Z0 + self.DISP_PCB_H / 2
        # camera stack along +X
        self.CAM_LENS_FRONT_X = self.FAIR_FRONT_X - self.LENS_RECESS
        self.CAM_PCB_FRONT_X = self.CAM_LENS_FRONT_X - self.CAM_LENS_PROJ
        self.CAM_PCB_BACK_X = self.CAM_PCB_FRONT_X - self.CAM_PCB_T
        self.CAM_PCB_CZ = self.CAM_AXIS_Z - self.CAM_OPT_OFF_Z
        # ESP32 stack along +Y from the left wall
        self.INNER_SIDE_Y = self.BODY_Y / 2 - self.WALL  # flat side wall, inner face |Y|
        self.ESP_TOP_FACE_Y = -self.INNER_SIDE_Y + self.ESP_WALL_GAP + self.ESP_TOP_POP
        self.ESP_BACK_FACE_Y = self.ESP_TOP_FACE_Y + self.ESP_T
        self.ESP_X0 = self.ESP_CX - self.ESP_L / 2
        self.ESP_X1 = self.ESP_CX + self.ESP_L / 2
        self.SEAM_Y = 0.0

    def report(self) -> str:
        lines = ["Unverified measurements (edit measurements/my_units.toml):"]
        for k in self.unverified:
            lines.append(f"  {k:22s} = {getattr(self, k):8.2f}   ({self._measured[k][1]})")
        return "\n".join(lines)


def load() -> P:
    return P()


if __name__ == "__main__":
    p = load()
    print(p.report())
    print(f"wire field depth behind a header: {p.WIRE_FIELD:.1f} mm")
