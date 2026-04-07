# AI Architecture: Multi-modal Data Pipeline

This document details the "brain" of the AI Photo Culling system, focusing on data ingestion, feature extraction, and automated decision logic.

## 1. Ingestion & State Management
To avoid memory overflow on high-volume datasets (e.g., 1000+ RAW files):

*   **Queue System**: The Python backend reads file paths and processes them in batches (e.g., 8 images/batch), optimized for M1 GPU (MPS).
*   **Async Processing**: AI runs in a separate thread/process to maintain UI responsiveness.
*   **Persistent State**: Analysis results (Scores, Coordinates, Face Vectors) are written to **SQLite** immediately after processing to support [Pause/Resume] functionality.

## 2. Multi-Layer Feature Extraction
Each image is analyzed across four independent data layers:

| Layer | Model | Feature Goal |
| :--- | :--- | :--- |
| **Spatial / Context** | **DINOv2 (ViT-L)** | 1024-dimensional vector embedding for "scene vibe", lighting, and background structure. |
| **Skeletal / Pose** | **YOLO-Pose / ViTPose** | (X, Y) coordinates of 17 body joints for posture and gesture analysis. |
| **Face & Gaze** | **InsightFace + L2CS-Net** | Eye-blink detection, gaze direction (Pitch/Yaw), and expression analysis. |
| **Technical Quality** | **LIQE (Blind IQA)** | Floating-point score for overall sharpness and edge blurring. |

## 3. Clustering Engine (Segmentation Logic)
The system avoids relying on timestamps by using visual intelligence for grouping.

### Phase 1: Scene Clustering (DBSCAN)
*   Uses **DBSCAN** on the 1024D DINOv2 vectors.
*   Identifies "Large Clusters" (e.g., all photos taken at the wedding arch) based on visual similarity.
*   Handles varying numbers of scenes automatically without pre-configuration.

### Phase 2: Pose Segmentation (Sub-clustering)
*   Within a Scene Cluster, calculates **Euclidean distance** between skeletal keypoints (e.g., hand vs. shoulder).
*   Detects sudden changes in pose (e.g., switching from "relaxed" to "heart gesture").
*   Segments the Scene Cluster into **Sub-clusters** representing specific poses.

## 4. Scoring & Decision Tree
Each image in a Sub-cluster is evaluated using a weighted formula:

### Weighted Scoring Formula
`Total Score = (Sharpness * 0.4) + (Eye Openness * 0.3) + (Smile/Expression * 0.2) + (Camera Gaze * 0.1)`

### The "Top K" Rule
*   **Small Clusters (1-2 photos)**: Selects the one with the highest score.
*   **Large Clusters (3+ photos)**: 
    1. Filter out images with high penalties (e.g., closed eyes, severe gaze offset).
    2. Select the top 1 (or 2) performers as the final "winners" for that pose/scene.
