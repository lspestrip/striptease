#include "src/simpleplot.h"
#include <QtCharts/QAbstractAxis>
#include <QtCharts/QSplineSeries>
#include <QtCharts/QValueAxis>
#include <QtCore/QRandomGenerator>
#include <QtCore/QDebug>

SimplePlot::SimplePlot(QChart* c) : _c(c){
}

void SimplePlot::line_add(const QString &name, const QColor &color){
    QPen pen(color);
    pen.setWidth(2);

    _series[name].reset(new QLineSeries(_c));
    _series[name]->setName(name);
    _series[name]->setPen(pen);

    _c->addSeries(_series[name].get());
}

void SimplePlot::line_color(const QString &name, const QColor &color){
    if(_series.find(name) != _series.end()){
        QPen pen(color);
        pen.setWidth(2);
        _series[name]->setPen(pen);
    }
}

void SimplePlot::line_remove(const QString &name){
     if(_series.find(name) != _series.end()){
         _c->removeSeries(_series[name].get());
         _series.erase(name);
     }
}

void SimplePlot::line_data(const QString &name, const std::vector<double> &mjd, const std::vector<double> &val){
    if(_series.find(name) != _series.end()){
        QVector<QPointF> points;
        points.reserve(mjd.size());
        for(size_t i=0; i< mjd.size(); i++){
            points.push_back(QPointF(mjd[i],val[i]));
        }
        _series[name]->replace(points);
    }
}


SimplePlot::~SimplePlot(){}
