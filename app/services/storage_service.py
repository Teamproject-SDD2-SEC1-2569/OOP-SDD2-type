import os
import time
import uuid
import logging
from typing import Tuple, Optional
import requests
from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def is_allowed_file(filename: str) -> bool:
    """ตรวจสอบนามสกุลไฟล์ที่อนุญาต"""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def upload_profile_image(file_storage, user_id: int) -> Tuple[bool, str]:
    """
    อัปโหลดรูปภาพโปรไฟล์ไปยัง OCI Object Storage (ผ่าน PAR)
    หาก OCI ล้มเหลวหรือไม่ได้ตั้งค่า จะ Fallback บันทึกลงเครื่องใน app/static/uploads/avatars/ อัตโนมัติ

    :param file_storage: Werkzeug FileStorage object จาก request.files
    :param user_id: รหัสผู้ใช้
    :return: (success: bool, image_url_or_error: str)
    """
    if not file_storage or not file_storage.filename:
        return False, "ไม่พบไฟล์ที่ต้องการอัปโหลด"

    original_filename = secure_filename(file_storage.filename)
    if not is_allowed_file(original_filename):
        return False, "รองรับเฉพาะไฟล์รูปภาพนามสกุล .png, .jpg, .jpeg, .gif, .webp เท่านั้น"

    ext = original_filename.rsplit(".", 1)[1].lower()
    unique_filename = f"avatar_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"

    # อ่านข้อมูลไฟล์
    try:
        file_bytes = file_storage.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        return False, "เกิดข้อผิดพลาดในการอ่านไฟล์"

    if len(file_bytes) > MAX_FILE_SIZE:
        return False, "ขนาดไฟล์ต้องไม่เกิน 5 MB"

    if len(file_bytes) == 0:
        return False, "ไฟล์รูปภาพว่างเปล่า"

    content_type = file_storage.mimetype or f"image/{ext}"

    # 1. ลองอัปโหลดไปยัง OCI Object Storage ผ่าน Pre-Authenticated Request (PAR)
    oci_par_url = (
        os.getenv("OCI_STORAGE_PAR_URL")
        or current_app.config.get("OCI_STORAGE_PAR_URL", "")
    ).strip()

    oci_public_prefix = (
        os.getenv("OCI_PUBLIC_URL_PREFIX")
        or current_app.config.get("OCI_PUBLIC_URL_PREFIX", "")
    ).strip()

    if oci_par_url:
        target_par_url = f"{oci_par_url.rstrip('/')}/{unique_filename}"
        try:
            logger.info(f"Attempting upload to OCI PAR: {target_par_url}")
            resp = requests.put(
                target_par_url,
                data=file_bytes,
                headers={"Content-Type": content_type},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Successfully uploaded to OCI: {unique_filename}")
                if oci_public_prefix:
                    public_url = f"{oci_public_prefix.rstrip('/')}/{unique_filename}"
                else:
                    public_url = target_par_url
                return True, public_url
            else:
                logger.warning(
                    f"OCI upload returned status {resp.status_code}: {resp.text[:200]}. Falling back to local storage."
                )
        except Exception as oci_err:
            logger.warning(f"OCI upload failed: {oci_err}. Falling back to local storage.")

    # 2. Fallback: บันทึกลง Local Static Directory
    try:
        upload_folder = os.path.join(current_app.root_path, "static", "uploads", "avatars")
        os.makedirs(upload_folder, exist_ok=True)
        local_file_path = os.path.join(upload_folder, unique_filename)

        with open(local_file_path, "wb") as f:
            f.write(file_bytes)

        local_url = f"/static/uploads/avatars/{unique_filename}"
        logger.info(f"Saved avatar locally: {local_url}")
        return True, local_url
    except Exception as local_err:
        logger.error(f"Local storage fallback failed: {local_err}")
        return False, "เกิดข้อผิดพลาดในการบันทึกรูปภาพลงระบบ"

