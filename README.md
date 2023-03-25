# TPD-Keys
#### Created by @TPD94, proxy function by Radziu

## Based on [pywidevine](https://cdm-project.com/Decryption-Tools/pywidevine "pywidevine")

How to use:
1. Create `TPD-Keys` folder.

2. Download and extract `tpd-keys.py`, `requirements.txt` and `DRMHeaders.py` into the newly created `TPD-Keys` directory

3. Install the requirements with `pip install -r requirements.txt`

4. Crete a WVD with pywidevine; `pywidevine create-device -k "KEY_PATH" -c "BLOB_PATH" -t "ANDROID" -l 3 -o "OUTPUT_PATH"`

5. Replace `MyWVD= "/PATH/TO/WVD.wvd"` with the path to your `.wvd` on line 15 of tpd-keys.py

> For instance 
> `MyWVD = "C:\Users\TPD94\Desktop\AndroidDeivce.wvd"`
> or if it is located in the same folder
> `MyWVD = "AndroidDeivce.wvd"`

6. Paste any needed headers into `DRMHeaders.py`

7. Run with `python tpd-keys.py`

8. Make a selection
