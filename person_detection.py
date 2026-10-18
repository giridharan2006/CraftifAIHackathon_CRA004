#!/usr/bin/env python3

import os
import cv2
import json
import time
from datetime import datetime, timezone
from ultralytics import YOLO

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "models",
    "yolov8n.onnx"
)

VIDEO_PATH = os.path.expanduser(
    "~/Downloads/19832500-hd_1920_1080_25fps.mp4"
)

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "outputs"
)

CONFIDENCE_THRESHOLD = 0.50
IMAGE_SIZE = 640


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    annotated_path = os.path.join(
        OUTPUT_DIR, "annotated_workplace.mp4"
    )
    json_path = os.path.join(
        OUTPUT_DIR, "person_detections.json"
    )

    if not os.path.isfile(MODEL_PATH):
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    if not os.path.isfile(VIDEO_PATH):
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    print("Loading YOLOv8 ONNX model...")
    model = YOLO(MODEL_PATH, task="detect")

    print("Opening workplace video...")
    cap = cv2.VideoCapture(VIDEO_PATH)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = cv2.VideoWriter(
        annotated_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )

    if not writer.isOpened():
        cap.release()
        raise RuntimeError("Could not create annotated output video.")

    records = []
    frame_index = 0
    start_time = time.perf_counter()

    print(f"Video resolution: {width}x{height}")
    print(f"FPS: {fps:.2f}; frames: {total_frames}")
    print("Detecting people using CPU inference...")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            result = model.predict(
                source=frame,
                conf=CONFIDENCE_THRESHOLD,
                imgsz=IMAGE_SIZE,
                classes=[0],
                device="cpu",
                verbose=False
            )[0]

            frame_detections = []

            if result.boxes is not None:
                for box in result.boxes:
                    xyxy = box.xyxy[0].cpu().tolist()
                    confidence = float(box.conf[0].cpu())

                    frame_detections.append({
                        "class": "person",
                        "class_id": 0,
                        "confidence": round(confidence, 5),
                        "bbox_xyxy": [
                            round(float(value), 2)
                            for value in xyxy
                        ]
                    })

            annotated_frame = result.plot()
            writer.write(annotated_frame)

            records.append({
                "frame_index": frame_index,
                "timestamp_seconds": round(frame_index / fps, 4),
                "detections": frame_detections
            })

            frame_index += 1

            if frame_index % 50 == 0:
                print(
                    f"Processed {frame_index}/{total_frames} frames; "
                    f"people detected in current frame: "
                    f"{len(frame_detections)}"
                )

    finally:
        cap.release()
        writer.release()

    elapsed = time.perf_counter() - start_time
    total_detections = sum(
        len(record["detections"]) for record in records
    )

    report = {
        "application": "Workplace Safety Sentinel",
        "task": "person_detection",
        "model": os.path.basename(MODEL_PATH),
        "input_video": VIDEO_PATH,
        "inference_provider": "CPUExecutionProvider",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "image_size": IMAGE_SIZE,
        "video_fps": fps,
        "video_resolution": [width, height],
        "frames_processed": frame_index,
        "total_person_detections": total_detections,
        "processing_time_seconds": round(elapsed, 3),
        "average_processing_fps": round(
            frame_index / elapsed, 3
        ) if elapsed > 0 else None,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "frames": records
    }

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\nDetection completed.")
    print(f"Frames processed: {frame_index}")
    print(f"Total person detections: {total_detections}")
    print(f"Processing time: {elapsed:.2f} seconds")
    print(f"Average processing FPS: {report['average_processing_fps']}")
    print(f"Annotated video: {annotated_path}")
    print(f"Detection JSON: {json_path}")


if __name__ == "__main__":
    main()
