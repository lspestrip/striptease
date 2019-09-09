#ifndef SIMPLEPLOT_H
#define SIMPLEPLOT_H

#include <map>
#include <vector>
#include <memory>
#include <QtCharts/QChart>
#include <QtCore/QTimer>

QT_CHARTS_BEGIN_NAMESPACE
class QLineSeries;
class QValueAxis;
QT_CHARTS_END_NAMESPACE

QT_CHARTS_USE_NAMESPACE

class SimplePlot: public QObject{
    Q_OBJECT
public:
    SimplePlot(QChart* c);
    virtual ~SimplePlot();

    void line_data(const QString& name,
                      const std::vector<double>& mjd,
                      const std::vector<double>& val);

    void line_add  (const QString& name,const QColor& color);
    void line_color(const QString& name,const QColor& color);
    void line_remove(const QString& name);
/*public slots:
    void handleTimeout();
*/

private:
    QChart* _c;
    std::map<QString,std::unique_ptr<QLineSeries>> _series;
};

#endif // SIMPLEPLOT_H
