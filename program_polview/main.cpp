#include "ui/mainwindow.h"
#include <QApplication>
#include "ui_mainwindow.h"

#include "src/simpleplot.h"
#include "src/stripconnection.hpp"
#include "src/data_stream.hpp"

#include <QtCharts/QAbstractAxis>
#include <QtCharts/QSplineSeries>
#include <QtCharts/QValueAxis>
#include <QtCore/QRandomGenerator>
#include <QtCore/QDebug>

#include <QTimer>


QT_CHARTS_BEGIN_NAMESPACE
class QSplineSeries;
class QValueAxis;
QT_CHARTS_END_NAMESPACE

#include <QJsonDocument>
#include <QJsonObject>
#include <QThread>
#include <QtNetwork/QNetworkAccessManager>
#include <QtNetwork/QNetworkRequest>
#include <QtNetwork/QNetworkReply>
#include <QtNetwork/QNetworkCookieJar>
#include <QtNetwork/QNetworkCookie>
#include <thread>         // std::this_thread::sleep_for
#include <chrono>         // std::chrono::seconds
#include <iostream>
#include "src/data_chart.hpp"
int main(int argc, char *argv[])
{
    data_stream d;
    d.start();
    //QtCharts::QChartView chartView;
    QApplication a(argc, argv);
    MainWindow w;


    data_chart c("DEM");
    c.line_add("G0_q1","PWRQ1",Qt::red,&d);
    c.line_add("G0_u1","PWRU1",Qt::green,&d);
    w.ui->temp->setChart(c.chart);
    w.show();

    QTimer timer;
    timer.callOnTimeout([&c](){c.update();});
    timer.start(100);

    return a.exec();

    d.join();

    //    qDebug() <<"status:"<< reply->error();
}
