#include "data_chart.hpp"
#include <limits>
#include <iostream>

using namespace  QtCharts;

data_chart::data_chart(const QString& name)
    : chart(new QChart()),
      _axisX(new QValueAxis()),
      _axisY(new QValueAxis())
{
    chart->createDefaultAxes();
    chart->setTitle(name);
    chart->addAxis(_axisX,Qt::AlignBottom);
    chart->addAxis(_axisY,Qt::AlignLeft);

    _axisX->setRange(0, 300);//FIXME
    _axisY->setLabelFormat("%.2e");
}
void data_chart::line_add  (const QString& name,const std::string& key,const QColor& color,data_stream* stream){
    chart_item item;
    item.key    = key;
    item.stream = stream;
    item.series.reset(new QLineSeries(chart));
    chart->addSeries(item.series.get());

    QPen pen(color);
    pen.setWidth(2);
    item.series->setPen(pen);
    item.series->attachAxis(_axisX);
    item.series->attachAxis(_axisY);
    item.series->setName(name);

    //chart->addSeries(item.series.get());
    _items.insert(std::make_pair(name,std::move(item)));
}

void data_chart::line_color(const QString& name,const QColor& color){
    QPen pen(color);
    pen.setWidth(2);
    _items.at(name).series->setPen(pen);
}

void data_chart::line_remove(const QString& name){
    chart->removeSeries(_items.at(name).series.get());
}

void data_chart::update(){
    double min = std::numeric_limits<double>::quiet_NaN();
    double max = std::numeric_limits<double>::quiet_NaN();

    auto mm = [&min,&max](const QVector<QPointF>& data){
        for(const auto& e: data){
            min = std::min(e.y(),min);
            max = std::max(e.y(),max);
        }
    };
    for(auto& item : _items){
        QVector<QPointF> data =item.second.stream->get(item.second.key);
        mm(data);
        //std::cout << data.size() << " " << min << " " << max << std::endl ;
        item.second.series->replace(data);
    }
    double delta = (max - min)*0.05;
   _axisY->setRange(min-delta,max+delta);
}
