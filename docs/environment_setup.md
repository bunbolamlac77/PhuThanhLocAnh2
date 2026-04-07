# Environment Setup: Mac M1 Standard

To ensure maximum compatibility and performance for AI models on Apple Silicon, follow these configuration steps.

## 1. Environment Manager (Miniforge)
Use **Miniforge** to manage Python environments (ARM64 native).

*   **Install Miniforge**: `brew install miniforge`
*   **Create Environment**:
    ```bash
    conda create -n ai_culling python=3.10
    conda activate ai_culling
    ```
*   **Note**: Python 3.10 is the target for stability with AI libraries like **InsightFace** and **MediaPipe** on ARM64.

## 2. Core AI (PyTorch + MPS)
Install the stable PyTorch version with support for Metal Performance Shaders (MPS).

*   **Install PyTorch**:
    ```bash
    pip install --pre torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/nightly/cpu
    ```
    *This automatically includes MPS support for the M1 GPU.*

## 3. Mandatory AI Dependencies
Install the required libraries for each layer of the pipeline:

```bash
pip install transformers ultralytics insightface mediapipe opencv-python fastapi uvicorn
```

*   **transformers**: For DINOv2.
*   **ultralytics**: For YOLO-Pose.
*   **insightface / mediapipe**: For Face/Gaze logic.
*   **fastapi / uvicorn**: For the local backend server.

## 4. Frontend & Desktop Environment
*   **Node.js**: Install `v20 (LTS)` (Required for React/Vite development).
*   **Rust Compiler**: Necessary for building Tauri (v2).
    ```bash
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    ```

## 5. Summary Table
| Component | Targeted Version |
| :--- | :--- |
| **OS** | macOS (Apple Silicon M1) |
| **Python** | 3.10.13 |
| **Node.js** | v20 LTS |
| **Rust** | Latest Stable |
| **PyTorch** | Latest with MPS Support |
