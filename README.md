# TPD-Keys
#### Created by @TPD94, proxy function by Radziu

## Based on [pywidevine](https://cdm-project.com/Decryption-Tools/pywidevine "pywidevine")

How to use:
1. Create `TPD-Keys` folder.

2. Download and extract `tpd-keys.py`, `requirements.txt` and `License_cURL.py` into the newly created `TPD-Keys` directory

3. Install the requirements with `pip install -r requirements.txt`

4. Crete a WVD with pywidevine; `pywidevine create-device -k "/PATH/TO/device_private_key" -c "/PATH/TO/device_client_id_blob" -t "ANDROID" -l 3`

5. Place your .wvd in the root of `TPD-Keys` directory

6. Paste any needed headers into `License_cURL.py`

7. Run with `python tpd-keys.py`

8. Make a selection
