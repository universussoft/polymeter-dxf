
---

# Polymeter DXF Processor

**Polymeter DXF Processor** is a Flask-based web application designed to process DXF (Drawing Exchange Format) files. It extracts polylines, assigns nodes, merges connected polylines into branches, and generates downloadable outputs including a CSV file, an updated DXF file, and a JPG preview.

---

## Features

- **DXF File Processing**: Upload a DXF file to extract and process polylines.
- **Node Assignment**: Automatically assigns unique node IDs to polyline start and end points.
- **Branch Merging**: Merges connected polylines into branches for simplified representation.
- **Output Generation**:
  - **CSV File**: Contains branch information (start node, end node, length, coordinates).
  - **Updated DXF File**: Includes original polylines and labeled nodes.
  - **JPG Preview**: Visual preview of the processed DXF file.
- **User-Friendly Interface**: Simple web interface for uploading and downloading files.

---

## Installation

To run the Polymeter DXF Processor locally, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/universussoft/polymeter-dxf.git
   cd polymeter-dxf
   ```

2. **Install Dependencies**:
   - Ensure you have Python 3.7 or higher installed.
   - Install the required Python packages:
     ```bash
     pip install -r requirements.txt
     ```

3. **Run the Flask Application**:
   ```bash
   python app.py
   ```

4. **Access the Application**:
   - Open your browser and navigate to `http://localhost:5000`.

---

## Usage

1. **Upload a DXF File**:
   - On the homepage, click the "Upload DXF" button and select a `.dxf` file.

2. **Process the File**:
   - The application will process the file and generate:
     - A CSV file with branch information.
     - An updated DXF file with labeled nodes.
     - A JPG preview of the processed DXF file.

3. **Download the Outputs**:
   - Click the provided links to download the CSV, DXF, and JPG files.

---

## API Endpoints

The application exposes the following endpoints:

- **`POST /process-dxf`**:
  - Upload a DXF file for processing.
  - Returns JSON with URLs to download the generated files.

- **`GET /download/<filename>`**:
  - Download the generated files (`final_branches.csv`, `dxf_preview.jpg`, `processed_output.dxf`).

---

## Code Structure

- **`app.py`**: Main Flask application with routes and processing logic.
- **`templates/`**: Contains the HTML template for the homepage (`index.html`).
- **`requirements.txt`**: Lists the Python dependencies.

---

## Dependencies

- **Flask**: Web framework for handling requests and serving files.
- **ezdxf**: Library for reading and writing DXF files.
- **Shapely**: Library for geometric operations (e.g., LineString).
- **Pandas**: Library for creating and exporting CSV files.
- **Pillow (PIL)**: Library for generating JPG previews.

---

## Contributing

We welcome contributions! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your commit message here"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a pull request on GitHub.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Support

If you encounter any issues or have questions, please open an issue on the [GitHub Issues Page](https://github.com/universussoft/polymeter-dxf/issues).

---

## Acknowledgments

- Thanks to the contributors and users of this project.
- Special thanks to the developers of the libraries used: Flask, ezdxf, Shapely, Pandas, and Pillow.

---

Enjoy using the Polymeter DXF Processor! 🚀

---
