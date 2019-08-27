#ifndef DATA_CHART_HPP
#define DATA_CHART_HPP

#include <QtCharts/QChart>
#include <QtCharts/QValueAxis>
#include <QtCharts/QLineSeries>
#include "data_stream.hpp"
#include <map>
#include <memory>


typedef struct{
    std::string                            key;
    data_stream*                           stream;
    std::unique_ptr<QtCharts::QLineSeries> series;
} chart_item;

class data_chart: public QObject{
    Q_OBJECT
public:
    QtCharts::QChart* chart;
    data_chart(const QString& name);
    void line_add  (const QString& name,const std::string& key,const QColor& color,data_stream* stream);
    void line_color(const QString& name,const QColor& color);
    void line_remove(const QString& name);
public slots:
    void update();
private:
    QtCharts::QValueAxis *_axisX;
    QtCharts::QValueAxis *_axisY;
    std::map<QString, chart_item> _items;
};

#endif // DATA_CHART_HPP
