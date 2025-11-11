import tarfile
import urllib.request
from pathlib import Path
from urllib.parse import urljoin
from typing import Set
import io

class APKAnalyzer:
    def __init__(self, repo_url: str, mode: str):
        self.repo_url = repo_url
        self.mode = mode
        self.download_dir = Path("downloads")
        self.download_dir.mkdir(exist_ok=True)
    
    def get_apk_path(self, package: str, version: str) -> Path:
        """Получает путь к APK-файлу"""
        apk_name = f"{package}-{version}.apk"
        
        if self.mode == "remote":
            apk_url = urljoin(self.repo_url, apk_name)
            apk_path = self.download_dir / apk_name
            
            print(f"Скачивание {apk_url} ...")
            try:
                urllib.request.urlretrieve(apk_url, apk_path)
            except Exception as e:
                raise RuntimeError(f"Не удалось скачать пакет: {e}")
            
            if not apk_path.exists() or apk_path.stat().st_size == 0:
                raise RuntimeError("Файл не скачался или пуст.")
            
            print(f"Скачано: {apk_path}")
            return apk_path
            
        else:  # local
            apk_path = Path(self.repo_url) / apk_name
            if not apk_path.exists():
                raise RuntimeError(f"Файл {apk_path} не найден локально.")
            print(f"Используется локальный файл: {apk_path}")
            return apk_path
    
    def extract_dependencies(self, apk_path: Path) -> Set[str]:
        """Извлекает зависимости из APK-файла"""
        print(f"Извлечение метаданных из {apk_path}...")
        
        with tarfile.open(apk_path, "r:gz") as tar:
            members = tar.getmembers()
            
            # Ищем .PKGINFO
            for member in members:
                if member.name == ".PKGINFO":
                    return self._parse_pkginfo(tar, member)
            
            # Ищем control.tar.gz
            for member in members:
                if member.name.endswith(("control.tar.gz", "control.tar")):
                    return self._parse_control_tar(tar, member)
        
        raise RuntimeError("Не удалось найти метаданные пакета")
    
    def _parse_pkginfo(self, tar: tarfile.TarFile, member: tarfile.TarInfo) -> Set[str]:
        """Парсит .PKGINFO файл"""
        f = tar.extractfile(member)
        content = f.read().decode("utf-8", errors="ignore")
        
        dependencies = set()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("depend = "):
                dep = line.split("=", 1)[1].strip()
                if dep:
                    dependencies.add(dep)
        
        print(f"Найдено зависимостей в .PKGINFO: {len(dependencies)}")
        return dependencies
    
    def _parse_control_tar(self, tar: tarfile.TarFile, member: tarfile.TarInfo) -> Set[str]:
        """Парсит control.tar.gz"""
        control_tar = tar.extractfile(member)
        if control_tar is None:
            return set()
        
        with tarfile.open(fileobj=io.BytesIO(control_tar.read())) as control_inner:
            for sub in control_inner.getmembers():
                if sub.name == "control":
                    f = control_inner.extractfile(sub)
                    content = f.read().decode("utf-8", errors="ignore")
                    
                    dependencies = set()
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith("Depends: "):
                            deps_str = line.split(":", 1)[1].strip()
                            for dep in deps_str.split(','):
                                dep = dep.strip()
                                if dep:
                                    dependencies.add(dep)
                    
                    print(f"Найдено зависимостей в control: {len(dependencies)}")
                    return dependencies
        
        return set()