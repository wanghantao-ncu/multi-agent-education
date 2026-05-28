"""
百度OCR文字识别服务 - 用于拍照错题本功能。
核心职责：
1. 调用百度通用文字识别API识别图片中的文字
2. 解析数学题目内容
3. 提取关键信息（题目、选项、答案等）
"""
import requests
import base64
import logging
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载环境变量（.env）
load_dotenv()

# 百度OCR API配置
BAIDU_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
BAIDU_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")
BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"


class OCRService:
    """百度OCR文字识别服务"""

    def __init__(self, api_key: str = BAIDU_API_KEY, secret_key: str = BAIDU_SECRET_KEY):
        """
        初始化OCR服务。

        Args:
            api_key: 百度API Key
            secret_key: 百度Secret Key
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.timeout = 15

    def _get_access_token(self) -> Optional[str]:
        """
        获取百度OCR API访问令牌。

        Returns:
            Optional[str]: 访问令牌，如果获取失败返回None
        """
        if not self.api_key or not self.secret_key:
            logger.error("缺少百度OCR凭证，请在 .env 中配置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")
            return None

        try:
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            response = requests.post(BAIDU_TOKEN_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            if not response.text.strip():
                logger.error("获取OCR令牌失败: 响应为空")
                return None

            try:
                result = response.json()
            except requests.exceptions.JSONDecodeError:
                logger.error("获取OCR令牌失败: 返回非JSON, status=%s, body=%s", response.status_code, response.text[:300])
                return None

            if "access_token" in result:
                self.access_token = result["access_token"]
                return self.access_token
            else:
                logger.error(f"获取OCR令牌失败: {result}")
                return None
        except requests.RequestException as e:
            logger.exception("获取OCR令牌请求异常", exc_info=e)
            return None
        except Exception as e:
            logger.exception("获取OCR令牌异常", exc_info=e)
            return None

    def recognize_text(self, image_path: str = None, image_base64: str = None) -> Optional[Dict[str, Any]]:
        """
        识别图片中的文字。

        Args:
            image_path: 图片文件路径（二选一）
            image_base64: Base64编码的图片数据（二选一）

        Returns:
            Optional[Dict[str, Any]]: 识别结果，包含文字内容和位置信息
        """
        if not image_path and not image_base64:
            logger.error("必须提供图片路径或Base64数据")
            return None

        # 获取访问令牌
        if not self.access_token:
            if not self._get_access_token():
                return None

        # 准备图片数据
        if image_path:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        else:
            image_data = image_base64

        # 调用OCR API
        try:
            params = {"access_token": self.access_token}
            data = {
                "image": image_data,
                "detect_direction": "false",
                "detect_language": "false",
                "paragraph": "false",
                "probability": "false",
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
            response = requests.post(
                BAIDU_OCR_URL,
                params=params,
                data=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            if not response.text.strip():
                logger.error("OCR识别失败: 接口返回空响应")
                return None

            try:
                result = response.json()
            except requests.exceptions.JSONDecodeError:
                logger.error("OCR识别失败: 返回非JSON, status=%s, body=%s", response.status_code, response.text[:300])
                return None

            if "words_result" in result:
                logger.debug(f"OCR识别成功，识别到{len(result['words_result'])}个文字块")
                return result
            else:
                if result.get("error_code"):
                    logger.error(
                        "OCR识别失败: error_code=%s, error_msg=%s",
                        result.get("error_code"),
                        result.get("error_msg"),
                    )
                logger.error(f"OCR识别失败: {result}")
                return None
        except requests.RequestException as e:
            logger.exception("OCR识别请求异常", exc_info=e)
            return None
        except Exception as e:
            logger.exception("OCR识别异常", exc_info=e)
            return None

    def extract_question(self, image_path: str = None, image_base64: str = None) -> Optional[str]:
        """
        提取图片中的题目文本。

        Args:
            image_path: 图片文件路径
            image_base64: Base64编码的图片数据

        Returns:
            Optional[str]: 提取的题目文本
        """
        result = self.recognize_text(image_path, image_base64)
        if not result or "words_result" not in result:
            return None

        # 将识别到的文字按顺序拼接
        words = [item["words"] for item in result["words_result"]]
        return "\n".join(words)

    def parse_math_question(self, image_path: str = None, image_base64: str = None) -> Optional[Dict[str, Any]]:
        """
        解析数学题目，提取题目内容、选项等信息。

        Args:
            image_path: 图片文件路径
            image_base64: Base64编码的图片数据

        Returns:
            Optional[Dict[str, Any]]: 解析后的题目信息
        """
        question_text = self.extract_question(image_path, image_base64)
        if not question_text:
            return None

        # 尝试解析题目结构
        lines = question_text.strip().split("\n")
        parsed = {
            "original_text": question_text,
            "question": "",
            "options": [],
            "answer": None,
            "analysis": None
        }

        # 简单的解析逻辑：第一行为题目，后续为选项
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 判断是否为选项（通常以A、B、C、D开头）
            if line.startswith(("A.", "B.", "C.", "D.", "A、", "B、", "C、", "D、", "A:", "B:", "C:", "D:")):
                option_text = line[2:].strip()
                parsed["options"].append({
                    "label": line[0],
                    "text": option_text
                })
            # 判断是否为答案（包含"答案"字样）
            elif "答案" in line or "参考答案" in line:
                parsed["answer"] = line.replace("答案", "").replace("：", "").replace(":", "").strip()
            # 判断是否为解析
            elif "解析" in line or "分析" in line:
                parsed["analysis"] = line.replace("解析", "").replace("分析", "").replace("：", "").replace(":", "").strip()
            # 默认作为题目内容
            else:
                if parsed["question"]:
                    parsed["question"] += "\n" + line
                else:
                    parsed["question"] = line

        return parsed


# 全局单例
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """
    获取OCR服务单例。

    Returns:
        OCRService: OCR服务实例
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
