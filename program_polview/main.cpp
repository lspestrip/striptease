#include "ui/mainwindow.h"
#include <QApplication>
#include "ui_mainwindow.h"

#include "src/simpleplot.h"
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

#include <memory>
#include <map>
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
#include <set>
#include <QCommandLineParser>
#include "src/data_chart.hpp"
#include "src/command_stream.hpp"

using namespace std::placeholders;
int main(int argc, char *argv[])
{
    std::map<QString,std::unique_ptr<data_stream>> d_stream;
    std::set<std::string> lna;

    command_stream cs;
    cs.start();

    QApplication app(argc, argv);
    MainWindow w;

    data_chart pwrQ1("Q1");
    data_chart pwrU1("U1");
    data_chart pwrQ2("Q2");
    data_chart pwrU2("U2");

    data_chart demQ1("Q1");
    data_chart demU1("U1");
    data_chart demQ2("Q2");
    data_chart demU2("U2");

    data_chart id("ID");
    data_chart ig("IG");
    data_chart vd("VD");
    data_chart vg("VG");

    w.ui->pwr_q1->setChart(pwrQ1.chart);
    w.ui->pwr_q2->setChart(pwrQ2.chart);
    w.ui->pwr_u1->setChart(pwrU1.chart);
    w.ui->pwr_u2->setChart(pwrU2.chart);

    w.ui->dem_q1->setChart(demQ1.chart);
    w.ui->dem_q2->setChart(demQ2.chart);
    w.ui->dem_u1->setChart(demU1.chart);
    w.ui->dem_u2->setChart(demU2.chart);

    w.ui->id->setChart(id.chart);
    w.ui->ig->setChart(ig.chart);
    w.ui->vd->setChart(vd.chart);
    w.ui->vg->setChart(vg.chart);



    /* ARGV MANAGEMENT BEGIN    */
    QCommandLineParser parser;
    parser.addHelpOption();
    parser.addOptions({
        {{"u", "user"}, "username for the login", "user"},
        {{"p", "password"}, "password for the login", "password"},
    });
    parser.process(app);
    /* ARGV MANAGEMENT END      */

    auto conf = command_stream::get_from_cin();

    if(conf.HasParseError()){
        std::cout << "PARSE ERROR" << std::endl;
        return 1;
    }
    for(auto& board : conf.GetArray()){
        QString name = board["name"].GetString();
        QTreeWidgetItem* board_item = new QTreeWidgetItem(w.ui->polarimeter_tree);
        board_item->setText(0,name);
        w.ui->polarimeter_tree->itemBelow(board_item);
        for(auto& pol : board["pols"].GetArray()){
            QTreeWidgetItem* pol_item = new QTreeWidgetItem(board_item);
            QString name = pol.GetString();
            pol_item->setText(0,name);
            pol_item->setCheckState(0,Qt::Unchecked);
            board_item->addChild(pol_item);
        }
    }
    /* LAMBDAS BEGIN*/
    auto l_get_key=[](const QString& pol,const std::string& name)->std::string{
        std::string key = pol.toStdString();
        key += "_HK";
        key += name[1]=='_'?name.substr(0,1):name.substr(0,2);
        return  key;
    };

    auto l_item_check = [&](QTreeWidgetItem* item,int){
        Qt::CheckState state= item->checkState(0);
        QString pol = item->text(0);
        if(state == Qt::Checked){
            std::string path = cs.add_pol(pol);
            data_stream* d = new data_stream(path);
            d_stream[pol].reset(d);
            d_stream[pol]->start();

            pwrQ1.line_add(pol,"PWRQ1",Qt::red,d);
            pwrQ2.line_add(pol,"PWRQ2",Qt::red,d);
            pwrU1.line_add(pol,"PWRU1",Qt::red,d);
            pwrU2.line_add(pol,"PWRU2",Qt::red,d);

            demQ1.line_add(pol,"DEMQ1",Qt::red,d);
            demQ2.line_add(pol,"DEMQ2",Qt::red,d);
            demU1.line_add(pol,"DEMU1",Qt::red,d);
            demU2.line_add(pol,"DEMU2",Qt::red,d);
            for(auto& name : lna){
                std::string key = l_get_key(pol,name);
                QString qkey = key.c_str();
                if(name[1]=='_'){
                    id.line_add(qkey,"ID"+name,Qt::red,d);
                    vd.line_add(qkey,"VD"+name,Qt::red,d);
                }
                ig.line_add(qkey,"IG"+name,Qt::red,d);
                vg.line_add(qkey,"VG"+name,Qt::red,d);
            }
        }else if(state == Qt::Unchecked){
            pwrQ1.line_remove(pol);
            pwrQ2.line_remove(pol);
            pwrU1.line_remove(pol);
            pwrU2.line_remove(pol);

            demQ1.line_remove(pol);
            demQ2.line_remove(pol);
            demU1.line_remove(pol);
            demU2.line_remove(pol);
            for(auto& name : lna){
                std::string key = l_get_key(pol,name);
                QString qkey = key.c_str();
                if(name[1]=='_'){
                    id.line_remove(qkey);
                    vd.line_remove(qkey);
                }
                ig.line_remove(qkey);
                vg.line_remove(qkey);
            }
            d_stream.at(pol)->stop();
            //d_stream.erase(pol);
            cs.del_pol(pol);
        }

        //std::cout << item->text(0).toStdString()<< " " << item->checkState(0) << std::endl;
    };

    auto l_update = [&](){
        if(!w.ui->tab_pwr->isHidden()){
            pwrQ1.update();
            pwrQ2.update();
            pwrU1.update();
            pwrU2.update();
        }else if(!w.ui->tab_dem->isHidden()){
            demQ1.update();
            demQ2.update();
            demU1.update();
            demU2.update();
        }else if(!w.ui->tab_lna->isHidden()){
            id.update();
            ig.update();
            vd.update();
            vg.update();
        }
    };



    auto l_lna = [&](int i,const std::string& name){
        for(auto& ds : d_stream){
            std::string key = l_get_key(ds.first,name);
            QString qkey = key.c_str();
            if(i==2){
                if(name[1]=='_'){
                    id.line_add(qkey,"ID"+name,Qt::red,ds.second.get());
                    vd.line_add(qkey,"VD"+name,Qt::red,ds.second.get());
                }
                ig.line_add(qkey,"IG"+name,Qt::red,ds.second.get());
                vg.line_add(qkey,"VG"+name,Qt::red,ds.second.get());
            }else if(i==0){
                if(name[1]=='_'){
                    id.line_remove(qkey);
                    vd.line_remove(qkey);
                }
                ig.line_remove(qkey);
                vg.line_remove(qkey);
            }
        }

        if(i==2){
            lna.insert(name);
        }else if(i==0){
            lna.erase(name);
        }

    };

    /* LAMBDAS END*/


    QObject::connect(w.ui->polarimeter_tree,&QTreeWidget::itemChanged,l_item_check);
    QObject::connect(w.ui->hk0,&QCheckBox::stateChanged,std::bind(l_lna,_1,"0_HK"));
    QObject::connect(w.ui->hk1,&QCheckBox::stateChanged,std::bind(l_lna,_1,"1_HK"));
    QObject::connect(w.ui->hk2,&QCheckBox::stateChanged,std::bind(l_lna,_1,"2_HK"));
    QObject::connect(w.ui->hk3,&QCheckBox::stateChanged,std::bind(l_lna,_1,"3_HK"));
    QObject::connect(w.ui->hk4,&QCheckBox::stateChanged,std::bind(l_lna,_1,"4_HK"));
    QObject::connect(w.ui->hk5,&QCheckBox::stateChanged,std::bind(l_lna,_1,"5_HK"));
    QObject::connect(w.ui->hk4a,&QCheckBox::stateChanged,std::bind(l_lna,_1,"4A_HK"));
    QObject::connect(w.ui->hk5a,&QCheckBox::stateChanged,std::bind(l_lna,_1,"5A_HK"));

    w.show();

    QTimer timer;
    timer.callOnTimeout(l_update);
    timer.start(100);

    //std::cout << "{\"user\":\""<<parser.value("user").toStdString() << "\",\"password\":\"" << parser.value("password").toStdString() << "\"}"<<std::endl;
    app.exec();

    for(auto& ds : d_stream){
        ds.second.reset();
        cs.del_pol(ds.first);
    }

    //    qDebug() <<"status:"<< reply->error();
}
