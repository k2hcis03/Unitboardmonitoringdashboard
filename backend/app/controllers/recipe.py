"""Recipe API controller"""
from litestar import Controller, get, post
from litestar.exceptions import NotFoundException
from typing import List, Dict
import json
import os
from pathlib import Path
import logging

from app.services.tcp_bridge import tcp_bridge

logger = logging.getLogger(__name__)

# Reference 디렉토리 경로 (프로젝트 루트 기준)
# backend/app/controllers/recipe.py -> backend/app/controllers -> backend/app -> backend -> 프로젝트 루트
REFERENCE_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".cursor" / "reference"

class RecipeController(Controller):
    """레시피 API 컨트롤러"""
    
    path = "/recipe"
    
    @get("/list", summary="레시피 파일 목록 조회")
    async def get_recipe_list(self) -> List[Dict[str, str]]:
        """reference 디렉토리의 JSON 파일 목록을 조회합니다.
        
        Returns:
            레시피 파일 목록 (파일명과 경로)
        """
        try:
            if not REFERENCE_DIR.exists():
                logger.warning(f"Reference directory not found: {REFERENCE_DIR}")
                return []
            
            recipe_files = []
            for file_path in REFERENCE_DIR.glob("*.json"):
                recipe_files.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(REFERENCE_DIR.parent.parent.parent.parent))
                })
            
            # 파일명으로 정렬
            recipe_files.sort(key=lambda x: x["filename"])
            logger.info(f"Found {len(recipe_files)} recipe files")
            return recipe_files
            
        except Exception as e:
            logger.error(f"Failed to list recipe files: {e}")
            return []
    
    @get("/{filename:str}", summary="레시피 파일 내용 조회")
    async def get_recipe_content(self, filename: str) -> Dict:
        """특정 레시피 파일의 내용을 조회합니다.
        
        Args:
            filename: 레시피 파일명 (예: ref1.json)
        
        Returns:
            레시피 JSON 데이터
        """
        try:
            file_path = REFERENCE_DIR / filename
            
            # 보안: 상위 디렉토리 접근 방지
            if not file_path.resolve().is_relative_to(REFERENCE_DIR.resolve()):
                raise NotFoundException("Invalid file path")
            
            if not file_path.exists():
                raise NotFoundException(f"Recipe file not found: {filename}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                recipe_data = json.load(f)
            
            logger.info(f"Loaded recipe file: {filename}")
            return recipe_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in recipe file {filename}: {e}")
            raise NotFoundException(f"Invalid JSON format in recipe file: {filename}")
        except Exception as e:
            logger.error(f"Failed to read recipe file {filename}: {e}")
            raise NotFoundException(f"Failed to read recipe file: {filename}")
    
    @post("/send", summary="레시피 전송")
    async def send_recipe(self, data: Dict) -> Dict[str, bool]:
        """선택한 레시피를 라즈베리파이로 전송합니다.
        
        Args:
            data: 레시피 데이터 (JSON 객체)
        
        Returns:
            전송 결과
        """
        try:
            # 레시피 데이터 검증
            if "CMD" not in data or data["CMD"] != "REF":
                raise ValueError("Invalid recipe format: CMD must be 'REF'")
            
            # TCP Bridge를 통해 라즈베리파이로 전송
            success = await tcp_bridge.send_recipe(data)
            
            if not success:
                raise Exception("Failed to send recipe to Raspberry Pi")
            
            logger.info(f"Recipe sent successfully: IDX={data.get('IDX')}, TANK_ID={data.get('TANK_ID')}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to send recipe: {e}")
            return {"success": False, "error": str(e)}
    
    @post("/send/{filename:str}", summary="레시피 파일 전송")
    async def send_recipe_file(self, filename: str) -> Dict[str, bool]:
        """레시피 파일을 읽어서 라즈베리파이로 전송합니다.
        
        Args:
            filename: 레시피 파일명 (예: ref1.json)
        
        Returns:
            전송 결과
        """
        try:
            # 레시피 파일 읽기
            recipe_data = await self.get_recipe_content(filename)
            
            # 레시피 전송
            result = await self.send_recipe(recipe_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send recipe file {filename}: {e}")
            return {"success": False, "error": str(e)}
