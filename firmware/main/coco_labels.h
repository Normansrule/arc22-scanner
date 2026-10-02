// The 80 COCO categories the detector knows, in model output order, with the
// Wikipedia article title used for the "learn more" lookup. The detector can
// ONLY name these 80 everyday things — it cannot identify species, minerals,
// brands or unknown objects.
#pragma once

struct CocoLabel {
    const char *name;
    const char *wiki;
};

static const CocoLabel kCoco[80] = {
    {"person", "Human"}, {"bicycle", "Bicycle"}, {"car", "Car"}, {"motorcycle", "Motorcycle"},
    {"airplane", "Airplane"}, {"bus", "Bus"}, {"train", "Train"}, {"truck", "Truck"}, {"boat", "Boat"},
    {"traffic light", "Traffic_light"}, {"fire hydrant", "Fire_hydrant"}, {"stop sign", "Stop_sign"},
    {"parking meter", "Parking_meter"}, {"bench", "Bench_(furniture)"}, {"bird", "Bird"}, {"cat", "Cat"},
    {"dog", "Dog"}, {"horse", "Horse"}, {"sheep", "Sheep"}, {"cow", "Cattle"}, {"elephant", "Elephant"},
    {"bear", "Bear"}, {"zebra", "Zebra"}, {"giraffe", "Giraffe"}, {"backpack", "Backpack"},
    {"umbrella", "Umbrella"}, {"handbag", "Handbag"}, {"tie", "Necktie"}, {"suitcase", "Suitcase"},
    {"frisbee", "Frisbee"}, {"skis", "Ski"}, {"snowboard", "Snowboard"}, {"sports ball", "Ball"},
    {"kite", "Kite"}, {"baseball bat", "Baseball_bat"}, {"baseball glove", "Baseball_glove"},
    {"skateboard", "Skateboard"}, {"surfboard", "Surfboard"}, {"tennis racket", "Racket_(sports_equipment)"},
    {"bottle", "Bottle"}, {"wine glass", "Wine_glass"}, {"cup", "Cup"}, {"fork", "Fork"}, {"knife", "Knife"},
    {"spoon", "Spoon"}, {"bowl", "Bowl"}, {"banana", "Banana"}, {"apple", "Apple"}, {"sandwich", "Sandwich"},
    {"orange", "Orange_(fruit)"}, {"broccoli", "Broccoli"}, {"carrot", "Carrot"}, {"hot dog", "Hot_dog"},
    {"pizza", "Pizza"}, {"donut", "Doughnut"}, {"cake", "Cake"}, {"chair", "Chair"}, {"couch", "Couch"},
    {"potted plant", "Houseplant"}, {"bed", "Bed"}, {"dining table", "Table_(furniture)"},
    {"toilet", "Toilet"}, {"tv", "Television"}, {"laptop", "Laptop"}, {"mouse", "Computer_mouse"},
    {"remote", "Remote_control"}, {"keyboard", "Computer_keyboard"}, {"cell phone", "Mobile_phone"},
    {"microwave", "Microwave_oven"}, {"oven", "Oven"}, {"toaster", "Toaster"}, {"sink", "Sink"},
    {"refrigerator", "Refrigerator"}, {"book", "Book"}, {"clock", "Clock"}, {"vase", "Vase"},
    {"scissors", "Scissors"}, {"teddy bear", "Teddy_bear"}, {"hair drier", "Hair_dryer"},
    {"toothbrush", "Toothbrush"},
};

static inline const CocoLabel &coco_label(int i) {
    static const CocoLabel unknown = {"?", "Object_detection"};
    return (i >= 0 && i < 80) ? kCoco[i] : unknown;
}
