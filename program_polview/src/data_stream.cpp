#define RAPIDJSON_HAS_STDSTRING 1
#include "data_stream.hpp"
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <iostream>
#include <thread>
#include "rapidjson/rapidjson.h"
#include "rapidjson/document.h"
#include "rapidjson/reader.h"
#include "rapidjson/filereadstream.h"
#include "rapidjson/istreamwrapper.h"
#include <iostream>
#include <fstream>      // std::ifstream
#include <ostream>
#include <boost/iostreams/device/file.hpp>
#include <boost/iostreams/stream.hpp>
#include <ext/stdio_filebuf.h>

#include "rapidjson/rapidjson.h"
#include "rapidjson/document.h"
#include "rapidjson/reader.h"
#include "rapidjson/filereadstream.h"
#include "rapidjson/istreamwrapper.h"
#include <iostream>
#include <fstream>      // std::ifstream
#include <stdio.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <sys/select.h>
#include <chrono>
#include <functional>
using namespace rapidjson;
using namespace std;
namespace io = boost::iostreams;
using namespace std::chrono;

std::set<std::string> data_stream::sci = {"DEMQ1","DEMU1","DEMU2","DEMQ2","PWRQ1","PWRU1","PWRU2","PWRQ2"};
std::set<std::string> data_stream::hk  = {
    "VD0_HK","VD1_HK","VD2_HK","VD3_HK","VD4_HK","VD5_HK",
    "ID0_HK","ID1_HK","ID2_HK","ID3_HK","ID4_HK","ID5_HK",
    "VG0_HK","VG1_HK","VG2_HK","VG3_HK","VG4_HK","VG5_HK","VG4A_HK","VG5A_HK",
    "IG0_HK","IG1_HK","IG2_HK","IG3_HK","IG4_HK","IG5_HK","IG4A_HK","IG5A_HK",
    "VPIN0_HK","VPIN1_HK","VPIN2_HK","VPIN3_HK",
    "IPIN0_HK","IPIN1_HK","IPIN2_HK","IPIN3_HK"
};

data_stream::data_stream(const string &path)
    : _go(true),
      _path(path),
      _ws(300),
      _last_mjd(0){

    for(auto& h : sci)
        _data[h];

    for(auto& h : hk)
        _data[h];
}

data_stream::~data_stream(){
    stop();
    _th.join();
}

void data_stream::start(){
    _th = std::thread(std::thread(std::bind(&data_stream::proceed, this)));
}


void data_stream::proceed(){

    ifstream ifs(_path, std::ifstream::in);
    std::cerr << "opened " << _path << std::endl;

    IStreamWrapper isw(ifs);

    while(_go){
        Document d;
        d.ParseStream<kParseStopWhenDoneFlag>(isw);

        if(d.HasParseError())
            std::cerr << "parse error, skipping" << std::endl;
        else
            decode(d);
    }
    std::cerr << "EXITING" << std::endl;
    ifs.close();
    remove(_path.c_str());
    std::cerr << "removed" << std::endl;
}

data_stream::stats_t data_stream::get_stats(){
    std::unique_lock lock(_m);
    stats_t map;

    for(auto& h : _data){
        if(h.second.second.empty())
            continue;
        if(sci.find(h.first) != sci.end())
            continue; // no SCI data on stats

        QString key = h.first.c_str();
        auto& v = h.second.second;
        double sum = std::accumulate(v.begin(), v.end(), 0.0);
        double mean = sum / v.size();

        std::vector<double> diff(v.size());
        std::transform(v.begin(), v.end(), diff.begin(), [mean](double x) { return x - mean; });
        double sq_sum = std::inner_product(diff.begin(), diff.end(), diff.begin(), 0.0);
        double stdev = std::sqrt(sq_sum / v.size());
        map[key].first  = mean;
        map[key].second = stdev;
    }
    return map;
}

void data_stream::decode(rapidjson::Document &d){
    std::unique_lock lock(_m);
    if(! d.HasMember("mjd"))
        return;
    double mjd = d["mjd"].GetDouble();
    for(auto& k : sci){
        if(d.HasMember(k)){
            _data[k].first.push_back(mjd);
            _data[k].second.push_back(d[k].GetInt64());
        }
    }
    if(d.HasMember("bias")){
        for(auto& k : hk){
            if(d["bias"].HasMember(k)){
                _data[k].first.push_back(mjd);
                _data[k].second.push_back(d["bias"][k].GetInt64());
            }
        }
    }
    if(mjd > _last_mjd)
        _last_mjd = mjd;

    //trim buffers to fit the window
    double mjd_cut = _last_mjd - (_ws/86400.);
    for(auto& item : _data){
        while(!item.second.first.empty() && item.second.first[0] < mjd_cut){
            item.second.first.pop_front();
            item.second.second.pop_front();
        }
    }
/*
    std::cout << "SCI " << _data["DEMQ1" ].second.size()<< std::endl;
    std::cout << "HK  " << _data["VD0_HK"].second.size()<< std::endl;
*/
}

double data_stream::w_sec(){
    return _ws;
}

void data_stream::w_sec(double ws){
    std::unique_lock lock(_m);
    _ws = ws;
}

data_stream::data_t data_stream::get(){
    std::unique_lock lock(_m);
    return _data;
}

QVector<QPointF> data_stream::get(const std::string& key){
    std::unique_lock lock(_m);
    QVector<QPointF> data;
    auto& src = _data[key];
    size_t size = src.first.size();
    if(size == 0){
        //std::cerr << "DATA EMPTY" << std::endl;
        return data;
    }
    data.reserve(size);
    for (size_t i=0; i<size; i++) {
        data.push_back(QPointF((_last_mjd - src.first[i])*86400.,src.second[i]));
    }
    //std::cerr << data.size() << " " << data.first().rx() <<" " << data.last().rx()<<std::endl;
    return data;
}
