import re
from pathlib import Path
from typing import Dict, Set, List

class TestRepository:
    def __init__(self, repo_file_path: str):
        self.repo_file_path = Path(repo_file_path)
        self.packages: Dict[str, Set[str]] = {}
        self.load_repository()
    
    def load_repository(self):
        """Загружает тестовый репозиторий из файла"""
        if not self.repo_file_path.exists():
            raise FileNotFoundError(f"Файл репозитория не найден: {self.repo_file_path}")
        
        print(f"Загрузка тестового репозитория из {self.repo_file_path}")
        
        with open(self.repo_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Формат: ПАКЕТ: зависимость1, зависимость2,...
                if ':' not in line:
                    print(f"Предупреждение: некорректная строка {line_num}: {line}")
                    continue
                
                package, deps_str = line.split(':', 1)
                package = package.strip().upper()
                
                # Извлекаем зависимости
                dependencies = set()
                for dep in deps_str.split(','):
                    dep = dep.strip().upper()
                    if dep and dep.isalpha():  # Только большие латинские буквы
                        dependencies.add(dep)
                
                self.packages[package] = dependencies
                print(f"Загружен пакет {package}: {dependencies}")
    
    def get_dependencies(self, package: str) -> Set[str]:
        """Возвращает зависимости для пакета"""
        package = package.upper()
        return self.packages.get(package, set())
    
    def package_exists(self, package: str) -> bool:
        """Проверяет существование пакета в репозитории"""
        return package.upper() in self.packages
    
    def list_packages(self) -> List[str]:
        """Возвращает список всех пакетов"""
        return sorted(self.packages.keys())