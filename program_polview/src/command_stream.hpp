#ifndef COMMAND_STREAM_HPP
#define COMMAND_STREAM_HPP

#include <QObject>
#include <thread>
#include <mutex>
#include "rapidjson/document.h"

class command_stream: public QObject{
    Q_OBJECT
public:
    static rapidjson::Document get_from_cin();
    command_stream();
    void start();
    void join(){_th.join();}
    std::string add_pol(const QString& pol);
    void del_pol(const QString& pol);
private:
    void loop();
    std::mutex _m;
    std::thread _th;
};

#endif // COMMAND_STREAM_HPP
