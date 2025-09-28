
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
# 导入QMT gateway
from vnpy_qmt.qmt_gateway import QmtGateway
from vnpy_ctastrategy import CtaEngine, CtaStrategyApp


def main():
    """Start VN Trader"""
    qapp = create_qapp()

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_app(CtaStrategyApp)
    # 添加gateway
    main_engine.add_gateway(QmtGateway, gateway_name="QMT")

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()