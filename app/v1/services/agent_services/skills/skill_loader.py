"""
Skill Loader - Load Agent Skills theo pattern Anthropic
Progressive disclosure: metadata (level 1) → SKILL.md (level 2) → supporting files (level 3)
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SkillLoader:
    """Load và quản lý Agent Skills theo pattern Anthropic"""
    
    def __init__(self, skills_dir: Optional[Path] = None):
        """
        Initialize Skill Loader
        
        Args:
            skills_dir: Path to skills directory (default: app/v1/services/agent_services/skills)
        """
        if skills_dir is None:
            # Default: skills directory relative to this file
            base_path = Path(__file__).parent
            self.skills_dir = base_path
        else:
            self.skills_dir = Path(skills_dir)
        
        self._skills_cache: Dict[str, Dict[str, Any]] = {}
    
    def load_skill_metadata(self, skill_dir: Path) -> Optional[Dict[str, str]]:
        """
        Load skill metadata (YAML frontmatter) từ SKILL.md (Level 1)
        
        Args:
            skill_dir: Path to skill directory
            
        Returns:
            Dict với 'name' và 'description', hoặc None nếu không tìm thấy
        """
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            logger.warning(f"SKILL.md not found in {skill_dir}")
            return None
        
        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML frontmatter
            if not content.startswith('---'):
                logger.warning(f"SKILL.md in {skill_dir} does not start with YAML frontmatter")
                return None
            
            # Extract frontmatter
            parts = content.split('---', 2)
            if len(parts) < 3:
                logger.warning(f"Invalid YAML frontmatter in {skill_dir}/SKILL.md")
                return None
            
            frontmatter = parts[1].strip()
            metadata = yaml.safe_load(frontmatter)
            
            if not isinstance(metadata, dict):
                logger.warning(f"YAML frontmatter is not a dict in {skill_dir}/SKILL.md")
                return None
            
            # Validate required fields
            if 'name' not in metadata or 'description' not in metadata:
                logger.warning(f"Missing 'name' or 'description' in {skill_dir}/SKILL.md")
                return None
            
            return {
                'name': metadata['name'],
                'description': metadata['description'],
                'skill_dir': str(skill_dir)
            }
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML frontmatter in {skill_dir}/SKILL.md: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading skill metadata from {skill_dir}: {e}")
            return None
    
    def load_all_skills(self) -> List[Dict[str, str]]:
        """
        Load metadata của tất cả skills (Level 1 - Progressive Disclosure)
        
        Returns:
            List of skill metadata dicts với 'name' và 'description'
        """
        skills = []
        
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return skills
        
        # Scan subdirectories trong skills_dir
        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                # Check if it's a skill directory (has SKILL.md)
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    metadata = self.load_skill_metadata(item)
                    if metadata:
                        skills.append(metadata)
                        # Cache for later use
                        self._skills_cache[metadata['name']] = {
                            'metadata': metadata,
                            'skill_dir': item
                        }
        
        logger.info(f"Loaded {len(skills)} skills from {self.skills_dir}")
        return skills
    
    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """
        Load full SKILL.md content khi agent trigger skill (Level 2)
        
        Args:
            skill_name: Name of the skill (from metadata)
            
        Returns:
            Full content of SKILL.md (without frontmatter), hoặc None nếu không tìm thấy
        """
        # Check cache first
        if skill_name in self._skills_cache:
            skill_dir = Path(self._skills_cache[skill_name]['skill_dir'])
        else:
            # Find skill directory
            skill_dir = None
            for item in self.skills_dir.iterdir():
                if item.is_dir():
                    metadata = self.load_skill_metadata(item)
                    if metadata and metadata['name'] == skill_name:
                        skill_dir = item
                        break
            
            if not skill_dir:
                logger.warning(f"Skill '{skill_name}' not found")
                return None
        
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        
        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove YAML frontmatter, return body only
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    return parts[2].strip()
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error loading skill content for '{skill_name}': {e}")
            return None
    
    def load_skill_file(self, skill_name: str, filename: str) -> Optional[str]:
        """
        Load supporting file từ skill directory (Level 3 - Progressive Disclosure)
        
        Args:
            skill_name: Name of the skill
            filename: Name of supporting file (e.g., 'reference.md', 'examples.md')
            
        Returns:
            Content of the file, hoặc None nếu không tìm thấy
        """
        # Find skill directory
        skill_dir = None
        if skill_name in self._skills_cache:
            skill_dir = Path(self._skills_cache[skill_name]['skill_dir'])
        else:
            for item in self.skills_dir.iterdir():
                if item.is_dir():
                    metadata = self.load_skill_metadata(item)
                    if metadata and metadata['name'] == skill_name:
                        skill_dir = item
                        break
        
        if not skill_dir:
            logger.warning(f"Skill '{skill_name}' not found")
            return None
        
        file_path = skill_dir / filename
        if not file_path.exists():
            logger.warning(f"File '{filename}' not found in skill '{skill_name}'")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading file '{filename}' from skill '{skill_name}': {e}")
            return None


# Singleton instance
_skill_loader = None

def get_skill_loader() -> SkillLoader:
    """Get singleton SkillLoader instance"""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader