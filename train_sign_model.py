import os
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

# === Config
IMG_SIZE = 128
DATASET_DIR = "dataset"  # Use your original dataset
BATCH_SIZE = 32
EPOCHS = 10

# === Load Data
images = []
labels = []

print("🔍 Inspecting dataset folder:", DATASET_DIR)
for label_folder in sorted(os.listdir(DATASET_DIR)):
    folder_path = os.path.join(DATASET_DIR, label_folder)
    print(f"📁 Folder: {folder_path}")
    if not os.path.isdir(folder_path):
        continue

    for img_file in os.listdir(folder_path):
        if img_file.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(folder_path, img_file)
            try:
                data = np.fromfile(img_path, dtype=np.uint8)
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("cv2.imdecode failed")
                img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                images.append(img)
                labels.append(label_folder)
                print("🖼️ Loaded:", img_path)
            except Exception as e:
                print(f"⚠️ Failed to load {img_path}: {e}")

print(f"\n✅ Total loaded images: {len(images)}")
if len(images) == 0:
    raise ValueError("❌ No images loaded. Check dataset folder and image files.")

# === Preprocess
images = np.array(images, dtype="float32") / 255.0
le = LabelEncoder()
labels_encoded = le.fit_transform(labels)
labels_encoded = tf.keras.utils.to_categorical(labels_encoded)

# === Save label map
os.makedirs("models", exist_ok=True)
label_map = {i: label for i, label in enumerate(le.classes_)}
np.save("models/label_map.npy", label_map)
print("✅ Saved label_map.npy:", label_map)

# === Train/Test Split
X_train, X_val, y_train, y_val = train_test_split(images, labels_encoded, test_size=0.2, random_state=42)

# === Build Model
base_model = MobileNetV2(include_top=False, input_shape=(IMG_SIZE, IMG_SIZE, 3), weights='imagenet')
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(128, activation="relu")(x)
output = Dense(y_train.shape[1], activation="softmax")(x)
model = Model(inputs=base_model.input, outputs=output)

for layer in base_model.layers:
    layer.trainable = False

model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
model.summary()

# === Train
datagen = ImageDataGenerator(
    rotation_range=10,
    zoom_range=0.1,
    width_shift_range=0.1,
    height_shift_range=0.1
)
datagen.fit(X_train)

history = model.fit(
    datagen.flow(X_train, y_train, batch_size=BATCH_SIZE),
    validation_data=(X_val, y_val),
    epochs=EPOCHS
)

# === Save model
model.save("models/asl_model.h5")
print("✅ Trained model saved to models/asl_model.h5")
