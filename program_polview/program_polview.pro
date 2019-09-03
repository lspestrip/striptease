#-------------------------------------------------
#
# Project created by QtCreator 2019-08-13T17:17:55
#
#-------------------------------------------------

QT       += core gui charts network
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = program_polview
TEMPLATE = app

# The following define makes your compiler emit warnings if you use
# any feature of Qt which has been marked as deprecated (the exact warnings
# depend on your compiler). Please consult the documentation of the
# deprecated API in order to know how to port your code away from it.
DEFINES += QT_DEPRECATED_WARNINGS

# You can also make your code fail to compile if you use deprecated APIs.
# In order to do so, uncomment the following line.
# You can also select to disable deprecated APIs only up to a certain version of Qt.
#DEFINES += QT_DISABLE_DEPRECATED_BEFORE=0x060000    # disables all the APIs deprecated before Qt 6.0.0

CONFIG += c++17

LIBS += -lssl -lcrypto -lboost_system -lboost_thread

SOURCES += \
        main.cpp \
        src/command_stream.cpp \
        src/data_chart.cpp \
        src/data_stream.cpp \
        src/simpleplot.cpp \
        ui/mainwindow.cpp

HEADERS += \
        src/command_stream.hpp \
        src/data_chart.hpp \
        src/data_stream.hpp \
        src/simpleplot.h \
        ui\mainwindow.h

FORMS += \
        ui/mainwindow.ui

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = ./bin
!isEmpty(target.path): INSTALLS += target
