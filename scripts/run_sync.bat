@echo off
cd /d E:\MyProject\MyTravelWork\MyTravelPanel
call venv\Scripts\activate.bat
python scripts\20260110_sync_invoice_payment_status.py %*
