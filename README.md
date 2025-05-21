# AppRecettes
Simple App to look for recipes

## Running the Script Locally

To run the `food5.py` script locally, follow these steps: First download and navigate to the unziped Folder of this repo then

1.  **Create a Python virtual environment:**
    Open your terminal or command prompt in the project's root directory and run:
    ```bash
    python -m venv .venv
    ```
    This will create a new directory named `.venv` which will contain the virtual environment.

2.  **Activate the virtual environment:**

    *   **On Windows:**
        ```bash
        .venv\Scripts\activate
        ```
    *   **On macOS and Linux:**
        ```bash
        source .venv/bin/activate
        ```
    You should see `(.venv)` at the beginning of your terminal prompt, indicating the virtual environment is active.

3.  **Install the required packages:**
    With the virtual environment active, install the dependencies listed in `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the script:**
    Finally, you can run the `food5.py` script:
    ```bash
    python food5.py
    ```
    The Flask development server will start, and you can access the application by opening your web browser and navigating to the address shown in the terminal (usually `http://127.0.0.1:5200`).
