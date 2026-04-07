# Development Roadmap: Phase-by-Phase Execution

This roadmap outlines the milestones for building the AI Photo Culling application on macOS (Apple Silicon).

## Step 1: Project Scaffolding
*   **Action**: Initialize Tauri v2 with `npm create tauri-app@latest`.
*   **Frameworks**: Select **React**, **TypeScript**, and **Vite**.
*   **Styling**: Install **TailwindCSS** and **Framer Motion**.
*   **Structure**: Create a `backend_ai` directory parallel to the frontend for Python logic.

## Step 2: Core AI & Backend API (Python)
*   **FastAPI**: Setup a local server (port 8000) for communication.
*   **Model Integration**:
    *   Load **DINOv2** for feature extraction.
    *   Setup **YOLO-Pose** for skeletal analysis.
    *   Integrate **InsightFace** and **L2CS-Net** for eye/gaze scoring.
*   **MPS Optimization**: Use `.to('mps')` on all models to leverage the M1 GPU/ANE.
*   **Pipeline Logic**: Function to process image batches and export results to **SQLite**.

## Step 3: React UI Development
*   **Screen 1 (Dropzone)**: Dark-themed dragging area with translucent glassmorphism.
*   **Screen 2 (Processing)**: Animated circular progress bar with real-time percentage updates.
*   **Screen 3 (Action)**: Results summary and large [COPY/MOVE] buttons.

## Step 4: System Integration
*   **Communication**: Frontend calls `POST /start-scan` with folder path.
*   **Progress Tracking**: Use **WebSockets** or Polling to pipe progress data from Python to React.
*   **Artifact Generation**: Python automatically creates `selected_files.txt` once the top-performing images are selected.

## Step 5: Packaging & Distribution
*   **Python Bundle**: Use `PyInstaller` to create a standalone binary of the AI environment.
*   **Tauri Build**: Configure `tauri.conf.json` to include the Python sidecar.
*   **Final Output**: Run `npm run tauri build` to generate the `.app` package for macOS.
