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
#include <QColorDialog>
#include <QLegendMarker>
#include <QFileDialog>
#include "src/data_chart.hpp"
#include "src/command_stream.hpp"
#include <fstream>
#include <iomanip>
#include <QDateTime>
#include <QPixmap>

#include <filesystem>
namespace fs = std::filesystem;

static std::vector<QString> hk_names = {
    "VD0_HK","VD1_HK","VD2_HK","VD3_HK","VD4_HK","VD5_HK",
    "ID0_HK","ID1_HK","ID2_HK","ID3_HK","ID4_HK","ID5_HK",
    "VG0_HK","VG1_HK","VG2_HK","VG3_HK","VG4_HK","VG5_HK","VG4A_HK","VG5A_HK",
    "IG0_HK","IG1_HK","IG2_HK","IG3_HK","IG4_HK","IG5_HK","IG4A_HK","IG5A_HK",
    "VPIN0_HK","VPIN1_HK","VPIN2_HK","VPIN3_HK",
    "IPIN0_HK","IPIN1_HK","IPIN2_HK","IPIN3_HK"
};

using namespace std::placeholders;

void write_csv(const QString& path, data_stream* s){
    std::ofstream f;
    std::cout << "opening:" << path.toStdString() << std::endl;
    f.open(path.toStdString());
    std::cout << "...ok" << std::endl;

    f << "name,mjd,value" << std::endl;
    data_stream::data_t d = s->get();
    for(auto& item : d){
        std::string name = item.first;
        for(size_t i=0; i<item.second.first.size(); i++){
            f<<name << "," << std::setprecision(15) << item.second.first[i] << "," << item.second.second[i] << std::endl;
        }
    }
    f.close();
}

int main(int argc, char *argv[])
{
    std::map<QString,std::unique_ptr<data_stream>> d_stream;
    std::set<std::string> lna;
    std::set<QString> pols;
    QString save_path;

    command_stream cs;
    cs.start();

    QApplication app(argc, argv);
    MainWindow w;

    int ws = w.ui->ws_spinbox->value();

    data_chart pwrQ1("Q1",ws);
    data_chart pwrU1("U1",ws);
    data_chart pwrQ2("Q2",ws);
    data_chart pwrU2("U2",ws);

    data_chart demQ1("Q1",ws);
    data_chart demU1("U1",ws);
    data_chart demQ2("Q2",ws);
    data_chart demU2("U2",ws);

    data_chart id("ID",ws);
    data_chart ig("IG",ws);
    data_chart vd("VD",ws);
    data_chart vg("VG",ws);

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

    QAction* ac_save_as = w.ui->menuFile->addAction("Save Directory");

    std::vector<data_chart*> charts = {
        &pwrQ1,&pwrQ2,&pwrU1,&pwrU2,
        &demQ1,&demQ2,&demU1,&demU2,
        &id,&ig,&vd,&vg};

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

    std::map<QString,std::map<QString,QTreeWidgetItem*>> m_stats;

    for(auto& board : conf.GetArray()){
        QString b_name = board["name"].GetString();
        QTreeWidgetItem* board_item = new QTreeWidgetItem(w.ui->stats_tree);
        board_item->setText(0,b_name);
        w.ui->stats_tree->itemBelow(board_item);
        for(auto& pol : board["pols"].GetArray()){
            QTreeWidgetItem* pol_item = new QTreeWidgetItem(board_item);
            QString p_name = pol.GetString();
            pol_item->setText(0,p_name);
            board_item->addChild(pol_item);
            for(const auto& hk : hk_names){
                QTreeWidgetItem* hk_item = new QTreeWidgetItem(pol_item);
                hk_item->setText(0,hk);
                hk_item->setText(1,"NaN");
                hk_item->setText(2,"NaN");
                pol_item->addChild(hk_item);
                m_stats[p_name][hk]=hk_item;
            }
        }
    }


    /* LAMBDAS BEGIN*/
    auto l_update_stats = [&](){
        for( auto& pol : m_stats){
            for(auto& hk : pol.second){
                hk.second->setText(1,"NaN");
                hk.second->setText(2,"NaN");
            }
        }
        for(auto& p : pols){
            auto m = d_stream.at(p)->get_stats();
            for(auto& s : m){
                QString mean;
                QString stdev;
                mean.sprintf("%.2e", s.second.first);
                stdev.sprintf("%.2e", s.second.second);
                m_stats.at(p).at(s.first)->setText(1,mean);
                m_stats.at(p).at(s.first)->setText(2,stdev);

            }
        }

    };

    auto l_marker_clicked = [&](QLegendMarker* m){
        QColor color = QColorDialog::getColor();
        for(auto c : charts){
            c->line_color(m->label(),color);
        }
    };

    auto l_legend_connect = [&](){
        for(auto c : charts){
            const auto markers = c->chart->legend()->markers();
            for (QLegendMarker *marker : markers) {
                marker->disconnect();
                QObject::connect(marker, &QLegendMarker::clicked,std::bind(l_marker_clicked,marker));
            }
        }

    };

    auto l_get_key=[](const QString& pol,const std::string& name)->std::string{
        std::string key = pol.toStdString();
        key += "_HK";
        key += name[1]=='_'?name.substr(0,1):name.substr(0,2);
        return  key;
    };

    auto l_ws = [&](int val){
        for(auto& pol : pols){
            d_stream.at(pol)->w_sec(val);
        }
        pwrQ1.w_sec(val);
        pwrQ2.w_sec(val);
        pwrU1.w_sec(val);
        pwrU2.w_sec(val);

        demQ1.w_sec(val);
        demQ2.w_sec(val);
        demU1.w_sec(val);
        demU2.w_sec(val);
        id.w_sec(val);
        vd.w_sec(val);
        ig.w_sec(val);
        vg.w_sec(val);
    };

    auto l_item_check = [&](QTreeWidgetItem* item,int){
        Qt::CheckState state= item->checkState(0);
        QString pol = item->text(0);
        if(state == Qt::Checked){
            pols.insert(pol);
            std::string path = cs.add_pol(pol);
            data_stream* d = new data_stream(path);
            d_stream[pol].reset(d);
            d_stream[pol]->start();

            pwrQ1.line_add(pol,"PWRQ1",Qt::gray,d);
            pwrQ2.line_add(pol,"PWRQ2",Qt::gray,d);
            pwrU1.line_add(pol,"PWRU1",Qt::gray,d);
            pwrU2.line_add(pol,"PWRU2",Qt::gray,d);

            demQ1.line_add(pol,"DEMQ1",Qt::gray,d);
            demQ2.line_add(pol,"DEMQ2",Qt::gray,d);
            demU1.line_add(pol,"DEMU1",Qt::gray,d);
            demU2.line_add(pol,"DEMU2",Qt::gray,d);
            for(auto& name : lna){
                std::string key = l_get_key(pol,name);
                QString qkey = key.c_str();
                if(name[1]=='_'){
                    id.line_add(qkey,"ID"+name,Qt::gray,d);
                    vd.line_add(qkey,"VD"+name,Qt::gray,d);
                }
                ig.line_add(qkey,"IG"+name,Qt::gray,d);
                vg.line_add(qkey,"VG"+name,Qt::gray,d);
            }
            l_legend_connect();
        }else if(state == Qt::Unchecked){
            pols.erase(pol);
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
        l_update_stats();
    };



    auto l_lna = [&](int i,const std::string& name){
        for(auto& pol : pols){
            std::string key = l_get_key(pol,name);
            QString qkey = key.c_str();
            if(i==2){
                if(name[1]=='_'){
                    id.line_add(qkey,"ID"+name,Qt::gray,d_stream.at(pol).get());
                    vd.line_add(qkey,"VD"+name,Qt::gray,d_stream.at(pol).get());
                }
                ig.line_add(qkey,"IG"+name,Qt::gray,d_stream.at(pol).get());
                vg.line_add(qkey,"VG"+name,Qt::gray,d_stream.at(pol).get());
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
        l_legend_connect();
    };

    auto l_save_as = [&](bool){
        QFileDialog dialog(&w);
        dialog.setWindowModality(Qt::WindowModal);
        dialog.setFileMode(QFileDialog::Directory);
        dialog.setOption(QFileDialog::ShowDirsOnly);
        dialog.setAcceptMode(QFileDialog::AcceptOpen);
        if(dialog.exec() == QDialog::Accepted){
            save_path = dialog.selectedFiles().first();
        }
    };

    auto l_save = [&](bool){
        if(save_path.isEmpty())
            l_save_as(true);
        if(save_path.isEmpty()){
            std::cout << "path not specified, no file will be saved!" << std::endl;
            return;
        }

        QString dt = QDateTime::currentDateTime().toString("yyyy_MM_dd_hh:mm:ss.zzz");
        QString path = save_path + "/" + dt;
        if(!fs::create_directories(path.toStdString())){
            std::cout << "CANNOT CREATE DIRECTORY: " << path.toStdString() << std::endl;
            return;
        }
        path += "/";
        for(const QString& p : pols){
            write_csv(path+p+".csv",d_stream.at(p).get());
        }
        pwrQ1.update();
        pwrQ2.update();
        pwrU1.update();
        pwrU2.update();

        demQ1.update();
        demQ2.update();
        demU1.update();
        demU2.update();

        id.update();
        ig.update();
        vd.update();
        vg.update();

        {
            QImage img(w.ui->pwr_q1->size(),QImage::Format_RGB32);
            img.fill(qRgba(0,0,0,0));
            QPainter paint(&img);

            w.ui->pwr_q1->render(&paint);
            img.save(path+"pwr_q1.png");

            w.ui->pwr_q2->render(&paint);
            img.save(path+"pwr_q2.png");

            w.ui->pwr_u1->render(&paint);
            img.save(path+"pwr_u1.png");

            w.ui->pwr_u2->render(&paint);
            img.save(path+"pwr_u2.png");
        }

        {
            QImage img(w.ui->dem_q1->size(),QImage::Format_RGB32);
            img.fill(qRgba(0,0,0,0));
            QPainter paint(&img);

            w.ui->dem_q1->render(&paint);
            img.save(path+"dem_q1.png");

            w.ui->dem_q2->render(&paint);
            img.save(path+"dem_q2.png");

            w.ui->dem_u1->render(&paint);
            img.save(path+"dem_u1.png");

            w.ui->dem_u2->render(&paint);
            img.save(path+"dem_u2.png");
        }
        {
            QImage img(w.ui->id->size(),QImage::Format_RGB32);
            img.fill(qRgba(0,0,0,0));
            QPainter paint(&img);

            w.ui->id->render(&paint);
            img.save(path+"id.png");

            w.ui->ig->render(&paint);
            img.save(path+"ig.png");

            w.ui->vd->render(&paint);
            img.save(path+"vd.png");

            w.ui->vg->render(&paint);
            img.save(path+"vg.png");
        }
    };
    /* LAMBDAS END*/

    /* SIGNALS BEGIN */
    QObject::connect(ac_save_as,&QAction::triggered,l_save_as);
    QObject::connect(w.ui->bt_save,&QPushButton::clicked,l_save);
    QObject::connect(w.ui->polarimeter_tree,&QTreeWidget::itemChanged,l_item_check);
    QObject::connect(w.ui->tab_group,&QTabWidget::currentChanged,[&](int){l_update();});
    QObject::connect(w.ui->hk0,&QCheckBox::stateChanged,std::bind(l_lna,_1,"0_HK"));
    QObject::connect(w.ui->hk1,&QCheckBox::stateChanged,std::bind(l_lna,_1,"1_HK"));
    QObject::connect(w.ui->hk2,&QCheckBox::stateChanged,std::bind(l_lna,_1,"2_HK"));
    QObject::connect(w.ui->hk3,&QCheckBox::stateChanged,std::bind(l_lna,_1,"3_HK"));
    QObject::connect(w.ui->hk4,&QCheckBox::stateChanged,std::bind(l_lna,_1,"4_HK"));
    QObject::connect(w.ui->hk5,&QCheckBox::stateChanged,std::bind(l_lna,_1,"5_HK"));
    QObject::connect(w.ui->hk4a,&QCheckBox::stateChanged,std::bind(l_lna,_1,"4A_HK"));
    QObject::connect(w.ui->hk5a,&QCheckBox::stateChanged,std::bind(l_lna,_1,"5A_HK"));
    /* SIGNALS END */

    void (QSpinBox::*fptr)(int) = &QSpinBox::valueChanged;
    QObject::connect(w.ui->ws_spinbox,fptr,l_ws);

    w.show();

    QTimer timer;
    timer.callOnTimeout(l_update);
    timer.start(1000);

    app.exec();

    for(auto& ds : d_stream){
        ds.second.reset();
        cs.del_pol(ds.first);
    }
}
