#define RAPIDJSON_HAS_STDSTRING 1
#include "command_stream.hpp"
#include <iostream>
#include <fstream>      // std::ifstream
#include "rapidjson/rapidjson.h"
#include "rapidjson/document.h"
#include "rapidjson/reader.h"
#include "rapidjson/filereadstream.h"
#include "rapidjson/istreamwrapper.h"
#include "rapidjson/ostreamwrapper.h"
#include "rapidjson/writer.h"
#include <iostream>
#include <string>
#include <stdlib.h>
#include <functional>   // std::bind

std::string randomString()
{
    std::string str = "AAAAAAAAAA";

    str[0] = rand() % 26 + 65;
    str[1] = rand() % 26 + 65;
    str[2] = rand() % 26 + 65;
    str[3] = rand() % 26 + 65;
    str[4] = rand() % 26 + 65;
    str[5] = rand() % 26 + 65;
    str[6] = rand() % 26 + 65;
    str[7] = rand() % 26 + 65;
    str[8] = rand() % 26 + 65;
    str[9] = rand() % 26 + 65;

    return str;
}
using namespace rapidjson;
command_stream::command_stream()
{

}
void command_stream::start(){
    _th = std::thread(std::thread(std::bind(&command_stream::loop, this)));
}

Document command_stream::get_from_cin(){
    IStreamWrapper isw(std::cin);
//    OStreamWrapper osw(std::cout);
    Document d;
    d.ParseStream<kParseStopWhenDoneFlag>(isw);

//    Writer writer(osw);
//    d.Accept(writer);
    return d;
}

void command_stream::loop(){
   // IStreamWrapper isw(std::cin);

}
#include <sys/types.h>
#include <sys/stat.h>

std::string command_stream::add_pol(const QString &pol){
    std::string pol_std = pol.toStdString();
    std::string path = "";
    int is_ok = 0;
    for(auto i=0; i<5; i++){
        path = "/tmp/strip."+pol_std+"."+randomString();
        //std::cerr << path << std::endl;
        is_ok = mkfifo(path.c_str(),S_IRUSR|S_IWUSR);
        if(is_ok != 0){
          //  std::cerr << strerror(errno) << std::endl;
        }else {
            break;
        }
    }
    if(is_ok != 0){
        throw std::runtime_error(strerror(errno));
    }

    Document d;
    d.SetObject();

    std::string cmd = "attach_pipe";

    Value val_cmd(kStringType);
    val_cmd.SetString(cmd.c_str(),cmd.size());

    Value val_pol(kStringType);
    val_pol.SetString(pol_std.c_str(),pol_std.size());

    Value val_path(kStringType);
    val_path.SetString(path.c_str(),path.size());


    d.AddMember("cmd",val_cmd,d.GetAllocator());
    d.AddMember("pol",val_pol,d.GetAllocator());
    d.AddMember("path",val_path,d.GetAllocator());

    std::cout.flush();
    OStreamWrapper osw(std::cout);
    Writer writer(osw);
    d.Accept(writer);
    std::cout.flush();

    return path;
}

void command_stream::del_pol(const QString &pol){
    std::string pol_std = pol.toStdString();

    Document d;
    d.SetObject();

    std::string cmd = "detach_pipe";

    Value val_cmd(kStringType);
    val_cmd.SetString(cmd.c_str(),cmd.size());

    Value val_pol(kStringType);
    val_pol.SetString(pol_std.c_str(),pol_std.size());


    d.AddMember("cmd",val_cmd,d.GetAllocator());
    d.AddMember("pol",val_pol,d.GetAllocator());

    std::cout.flush();
    OStreamWrapper osw(std::cout);
    Writer writer(osw);
    d.Accept(writer);
    std::cout.flush();
}
