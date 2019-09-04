#ifndef DATA_STREAM_HPP
#define DATA_STREAM_HPP

#include <boost/asio.hpp>
#include <thread>
#include "rapidjson/document.h"
#include <deque>
#include <set>
#include <QVector>
#include <QPointF>
#include <mutex>
class data_stream
{
public:
    typedef std::deque<double> buffer_t;
    typedef std::pair<buffer_t,buffer_t> data_t;
    typedef std::map<QString,std::pair<double,double>> stats_t;

    double w_sec();
    void w_sec(double ws);
    data_stream(const std::string& path);
    ~data_stream();
    void start();
    void stop(){_go = false;}
    void join(){_th.join();}

    QVector<QPointF> get(const std::string& key);
    stats_t get_stats();

private:
    bool _go;
    std::string _path;
    std::mutex _m;
    double _ws;
    double _last_mjd;
    void proceed();
    void decode(rapidjson::Document& d);

    std::map<std::string,data_t> _data;
    static std::set<std::string> sci;
    static std::set<std::string> hk;

    std::thread _th;
};

#endif // DATA_STREAM_HPP
