"""WebView 截图抽象接口"""

from abc import ABC, abstractmethod


class Screenshotter(ABC):
    """WebView 截图抽象接口"""

    @abstractmethod
    def capture_html(self, html: str) -> str:
        """
        将 HTML 渲染为长图截图。
        返回: 临时文件路径
        """
        ...
